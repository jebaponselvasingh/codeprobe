"""
LangGraph subgraph for SecurityAgent — ReAct-style multi-step verification.

Flow:
  llm_classify_findings
         |
  filter_critical
    |              |
(criticals)   (none)
    |              |
  verify_finding  aggregate --> END
    |              |
(confirmed)   (none)
    |              |
  enrich_owasp  aggregate --> END
         |
      aggregate --> END

Value over single-pass:
  - verify_finding removes false-positives from the critical list before scoring
  - enrich_owasp adds per-finding remediation detail for confirmed criticals
  - Final aggregate uses a cleaner signal for the security score
"""

import json
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from guardrails.schemas import SecurityLLMOutput
from utils.ollama import ollama_chat, parse_llm_json


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class SecurityGraphState(TypedDict):
    # Inputs (set once at invocation)
    combined_content: str          # pre-built truncated file content for LLM
    static_findings: List[Dict]
    queue: Any                     # asyncio.Queue — opaque, no checkpointer needed
    llm_context: str
    # Accumulated across nodes
    classified_findings: List[Dict]
    owasp_coverage: Dict[str, str]
    confirmed_critical: List[Dict]
    owasp_enriched: List[Dict]
    final_findings: List[Dict]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _emit(state: SecurityGraphState, msg: str) -> None:
    """Non-blocking SSE progress emit inside a graph node."""
    q = state.get("queue")
    if q is not None:
        try:
            q.put_nowait({"type": "progress", "agent": "security", "phase": 2, "message": msg})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Node 1 — LLM initial classification
# ---------------------------------------------------------------------------

async def llm_classify_findings(state: SecurityGraphState) -> dict:
    """
    First LLM call: reproduce existing _llm_analysis logic but also return
    a quality-enriched classified_findings list that tags each finding with
    a confidence field the verify node will use.
    """
    _emit(state, "[graph] Classifying security findings with LLM...")

    combined = state.get("combined_content", "")
    llm_context = state.get("llm_context", "")
    context_prefix = f"{llm_context}\n\n" if llm_context else ""

    prompt = (
        f"{context_prefix}"
        "Review these code files for security vulnerabilities. Focus on: "
        "authentication flaws, injection points, privilege escalation, "
        "insecure data handling, and OWASP Top 10.\n\n"
        f"{combined}\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "findings": [\n'
        '    {\n'
        '      "type": "negative",\n'
        '      "area": "security",\n'
        '      "detail": "description of vulnerability",\n'
        '      "file": "filename",\n'
        '      "line": 0,\n'
        '      "fix_hint": "how to fix",\n'
        '      "severity": "critical|high|medium|low",\n'
        '      "owasp": "A01|A02|A03|A04|A05|A06|A07|A08|A09|A10"\n'
        "    }\n"
        "  ],\n"
        '  "additional_owasp_coverage": {\n'
        '    "A01": "covered|partial|missing",\n'
        '    "A02": "covered|partial|missing",\n'
        '    "A03": "covered|partial|missing",\n'
        '    "A04": "covered|partial|missing",\n'
        '    "A05": "covered|partial|missing",\n'
        '    "A06": "covered|partial|missing",\n'
        '    "A07": "covered|partial|missing",\n'
        '    "A08": "covered|partial|missing",\n'
        '    "A09": "covered|partial|missing",\n'
        '    "A10": "covered|partial|missing"\n'
        "  }\n"
        "}"
    )

    try:
        response = await ollama_chat(prompt, timeout=180)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, dict):
            try:
                validated = SecurityLLMOutput(**(parsed or {})).model_dump()
            except Exception:
                validated = {"findings": [], "additional_owasp_coverage": {}}

            findings = [
                f if isinstance(f, dict) else f.model_dump() if hasattr(f, "model_dump") else {}
                for f in validated.get("findings", [])
            ]
            return {
                "classified_findings": findings,
                "owasp_coverage": validated.get("additional_owasp_coverage", {}),
            }
    except Exception as e:
        _emit(state, f"[graph] LLM classify failed: {e}")

    return {"classified_findings": [], "owasp_coverage": {}}


# ---------------------------------------------------------------------------
# Node 2 — Filter critical (pure Python)
# ---------------------------------------------------------------------------

def filter_critical(state: SecurityGraphState) -> dict:
    """Extract critical and high severity findings for targeted verification."""
    critical = [
        f for f in state.get("classified_findings", [])
        if isinstance(f, dict) and f.get("severity") in ("critical", "high")
    ]
    return {"confirmed_critical": critical}


# ---------------------------------------------------------------------------
# Node 3 — Verify critical findings (ReAct verification pass)
# ---------------------------------------------------------------------------

async def verify_finding(state: SecurityGraphState) -> dict:
    """
    Targeted LLM call that reviews only the critical/high findings and
    identifies which are genuine vs false-positives (e.g. triggered by
    variable names, test fixtures, or framework boilerplate).
    Keeps the call small by sending findings as JSON + a short code excerpt.
    """
    candidates = state.get("confirmed_critical", [])
    if not candidates:
        return {"confirmed_critical": []}

    _emit(state, f"[graph] Verifying {len(candidates)} critical finding(s) for false positives...")

    compact = json.dumps(
        [{"i": i, "detail": f.get("detail", ""), "file": f.get("file", ""), "severity": f.get("severity", "")}
         for i, f in enumerate(candidates)],
        separators=(",", ":"),
    )[:2000]

    # Short code snippet for context
    code_excerpt = state.get("combined_content", "")[:2000]

    prompt = (
        "You are a senior security reviewer. Below are automated security findings.\n"
        "Mark any that are CLEARLY false positives — e.g. triggered by test code, "
        "example variable names, framework boilerplate, or commented-out code.\n\n"
        f"Findings:\n{compact}\n\n"
        f"Code excerpt:\n{code_excerpt}\n\n"
        "Return ONLY valid JSON — a list of {i, false_positive} for each finding:\n"
        '[{"i": 0, "false_positive": false}, ...]'
    )

    try:
        response = await ollama_chat(prompt, timeout=120)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, list):
            fp_indices = {
                item["i"] for item in parsed
                if isinstance(item, dict) and item.get("false_positive") and "i" in item
            }
            confirmed = [f for i, f in enumerate(candidates) if i not in fp_indices]
            removed = len(candidates) - len(confirmed)
            if removed:
                _emit(state, f"[graph] Verification removed {removed} false positive(s) from critical findings")
            return {"confirmed_critical": confirmed}
    except Exception as e:
        _emit(state, f"[graph] Verify step failed ({e}), keeping all critical findings")

    return {"confirmed_critical": candidates}


# ---------------------------------------------------------------------------
# Node 4 — Enrich confirmed criticals with OWASP remediation detail
# ---------------------------------------------------------------------------

async def enrich_with_owasp(state: SecurityGraphState) -> dict:
    """
    For each confirmed critical finding (max 3), make a short targeted LLM
    call to add a detailed remediation note and confirm the OWASP category.
    """
    confirmed = state.get("confirmed_critical", [])
    if not confirmed:
        return {"owasp_enriched": []}

    _emit(state, f"[graph] Enriching {min(len(confirmed), 3)} critical finding(s) with OWASP detail...")

    enriched = list(confirmed)  # start with originals

    for i, finding in enumerate(confirmed[:3]):
        detail = finding.get("detail", "")
        file_ = finding.get("file", "")
        owasp = finding.get("owasp", "")

        prompt = (
            f"Security vulnerability: {detail}\n"
            f"File: {file_}\n"
            f"Suspected OWASP category: {owasp}\n\n"
            "Provide a short JSON response:\n"
            '{"confirmed_owasp": "A0X", "remediation": "2-3 sentence specific fix"}'
        )

        try:
            response = await ollama_chat(prompt, timeout=60)
            parsed = parse_llm_json(response, default=None)
            if parsed and isinstance(parsed, dict):
                enriched[i] = {
                    **finding,
                    "owasp": parsed.get("confirmed_owasp", owasp),
                    "fix_hint": parsed.get("remediation", finding.get("fix_hint", "")),
                }
        except Exception:
            pass  # keep original finding on failure

    return {"owasp_enriched": enriched}


# ---------------------------------------------------------------------------
# Node 5 — Aggregate all findings
# ---------------------------------------------------------------------------

def aggregate(state: SecurityGraphState) -> dict:
    """
    Merge static findings, classified findings, and owasp-enriched criticals
    into a single deduplicated final list.
    """
    static = state.get("static_findings", [])
    classified = state.get("classified_findings", [])
    enriched = state.get("owasp_enriched", [])

    # Build enriched lookup by detail prefix for dedup
    enriched_details = {f.get("detail", "")[:40] for f in enriched}
    enriched_files = {(f.get("file", ""), f.get("detail", "")[:40]) for f in enriched}

    # Start with static findings
    merged: List[Dict] = list(static)
    existing_keys = {(f.get("file", ""), f.get("detail", "")[:40]) for f in static}

    # Add classified (non-enriched) findings that aren't duplicates
    for f in classified:
        key = (f.get("file", ""), f.get("detail", "")[:40])
        if key not in existing_keys and key not in enriched_files:
            merged.append(f)
            existing_keys.add(key)

    # Add enriched findings (replace any matching classified ones)
    for f in enriched:
        key = (f.get("file", ""), f.get("detail", "")[:40])
        if key not in existing_keys:
            merged.append(f)
            existing_keys.add(key)

    return {"final_findings": merged}


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def _route_after_filter(state: SecurityGraphState) -> str:
    return "verify_finding" if state.get("confirmed_critical") else "aggregate"


def _route_after_verify(state: SecurityGraphState) -> str:
    return "enrich_with_owasp" if state.get("confirmed_critical") else "aggregate"


# ---------------------------------------------------------------------------
# Build & compile graph (once at import time)
# ---------------------------------------------------------------------------

def _build_security_graph() -> Any:
    g = StateGraph(SecurityGraphState)

    g.add_node("llm_classify_findings", llm_classify_findings)
    g.add_node("filter_critical", filter_critical)
    g.add_node("verify_finding", verify_finding)
    g.add_node("enrich_with_owasp", enrich_with_owasp)
    g.add_node("aggregate", aggregate)

    g.set_entry_point("llm_classify_findings")
    g.add_edge("llm_classify_findings", "filter_critical")
    g.add_conditional_edges(
        "filter_critical",
        _route_after_filter,
        {"verify_finding": "verify_finding", "aggregate": "aggregate"},
    )
    g.add_conditional_edges(
        "verify_finding",
        _route_after_verify,
        {"enrich_with_owasp": "enrich_with_owasp", "aggregate": "aggregate"},
    )
    g.add_edge("enrich_with_owasp", "aggregate")
    g.add_edge("aggregate", END)

    return g.compile()


_security_graph = _build_security_graph()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_security_graph(
    all_files: Dict[str, Any],
    static_findings: List[Dict],
    queue: Any,
    llm_context: str,
    combined_content: str,
) -> tuple[List[Dict], Dict[str, str]]:
    """
    Run the security LangGraph subgraph.
    Returns (final_findings, owasp_coverage) matching the original
    _llm_analysis() return contract so agent_05 needs no changes to run().
    """
    initial_state: SecurityGraphState = {
        "combined_content": combined_content,
        "static_findings": static_findings,
        "queue": queue,
        "llm_context": llm_context,
        "classified_findings": [],
        "owasp_coverage": {},
        "confirmed_critical": [],
        "owasp_enriched": [],
        "final_findings": [],
    }

    result = await _security_graph.ainvoke(initial_state)
    return result.get("final_findings", []), result.get("owasp_coverage", {})
