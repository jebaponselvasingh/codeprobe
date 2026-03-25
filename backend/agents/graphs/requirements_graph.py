"""
LangGraph subgraph for RequirementsAgent — cyclic retry loop.

Flow:
  parse_requirements
         |
  search_evidence   (pure Python, no LLM)
         |
  validate_requirements
         |
  [coverage_score < 6.0 AND retry_count < 3]?
    yes --> targeted_retry --> back to validate_requirements
    no  --> generate_scenarios --> END

Value over linear 5-pass:
  - If Pass 3 finds low coverage (many 'missing'), targeted_retry re-examines
    only the missing requirements with a more focused prompt and additional
    code context, giving the LLM a second (and third) chance to find evidence.
  - This catches cases where the initial evidence_search used the wrong keywords
    or the LLM missed implicit implementations.
"""

import json
import re
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from guardrails.schemas import (
    FlowTracingOutput,
    RequirementsParseOutput,
    TestScenariosOutput,
    ValidationOutput,
    clamp_score,
)
from utils.ollama import ollama_chat, parse_llm_json

_RETRY_COVERAGE_THRESHOLD = 6.0
_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class RequirementsGraphState(TypedDict):
    # Inputs
    problem_statement: str
    all_files: Dict[str, Any]
    all_code: str
    queue: Any
    llm_context: str
    # Intermediate
    parsed_requirements: List[Dict]
    implicit_requirements: List[Dict]
    evidence_map: Dict[str, List[Dict]]
    validation_results: List[Dict]
    coverage_score: float
    retry_count: int
    # Outputs
    flow_validations: List[Dict]
    test_scenarios: List[Dict]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _emit(state: RequirementsGraphState, msg: str) -> None:
    q = state.get("queue")
    if q is not None:
        try:
            q.put_nowait({"type": "progress", "agent": "requirements", "phase": 3, "message": msg})
        except Exception:
            pass


def _json_compact(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), default=str)


def _compute_coverage(validation_results: List[Dict]) -> float:
    total = len(validation_results)
    if total == 0:
        return 5.0
    implemented = sum(1 for r in validation_results if r.get("status") == "implemented")
    partial = sum(1 for r in validation_results if r.get("status") == "partial")
    return clamp_score((implemented + partial * 0.5) / total * 10)


# ---------------------------------------------------------------------------
# Node 1 — Parse requirements (Pass 1)
# ---------------------------------------------------------------------------

async def parse_requirements(state: RequirementsGraphState) -> dict:
    _emit(state, "[graph] Pass 1: Parsing requirements from problem statement...")

    problem_statement = state["problem_statement"]
    queue = state.get("queue")

    prompt = f"""Parse the following project problem statement into structured requirements.

Problem Statement:
{problem_statement}

Return ONLY valid JSON:
{{
  "explicit_requirements": [
    {{"id": "REQ-001", "category": "functional|authentication|data|ui|api|other", "description": "requirement text", "priority": "must|should|nice-to-have", "acceptance_criteria": ["criterion1"]}}
  ],
  "implicit_requirements": [
    {{"id": "IMP-001", "description": "implied requirement (e.g., error handling, loading states)", "category": "ux|security|performance|reliability"}}
  ]
}}

Extract ALL explicit requirements stated and infer reasonable implicit requirements."""

    try:
        response = await ollama_chat(prompt, timeout=120)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, dict):
            try:
                validated = RequirementsParseOutput(**parsed).model_dump()
            except Exception:
                validated = {"explicit_requirements": [], "implicit_requirements": []}
            explicit = validated.get("explicit_requirements", [])
            implicit = validated.get("implicit_requirements", [])
            if explicit:
                return {"parsed_requirements": explicit, "implicit_requirements": implicit}
    except Exception as e:
        _emit(state, f"[graph] Pass 1 failed: {e}")

    # Fallback: parse problem statement lines
    lines = [
        l.strip() for l in problem_statement.splitlines()
        if l.strip() and len(l.strip()) > 10
    ]
    fallback = [
        {"id": f"REQ-{i+1:03d}", "category": "functional", "description": line,
         "priority": "must", "acceptance_criteria": []}
        for i, line in enumerate(lines[:20])
    ]
    return {"parsed_requirements": fallback, "implicit_requirements": []}


# ---------------------------------------------------------------------------
# Node 2 — Static evidence search (no LLM, pure Python)
# ---------------------------------------------------------------------------

def search_evidence(state: RequirementsGraphState) -> dict:
    _emit(state, "[graph] Pass 2: Searching code for requirement evidence...")

    requirements = state.get("parsed_requirements", [])
    all_files = state.get("all_files", {})
    evidence_map: Dict[str, List[Dict]] = {}
    stop_words = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
                  "of", "is", "are", "be", "that", "this", "it", "with"}

    for req in requirements:
        req_id = req.get("id", "")
        description = req.get("description", "").lower()
        words = re.findall(r"\b[a-z]{3,}\b", description)
        keywords = [w for w in words if w not in stop_words][:8]
        evidence_list = []

        for path, entry in all_files.items():
            content = entry.get("content", "") if isinstance(entry, dict) else ""
            content_lower = content.lower()
            matches = []
            for kw in keywords:
                if kw in content_lower:
                    lines = content.splitlines()
                    for i, line in enumerate(lines[:200], start=1):
                        if kw.lower() in line.lower():
                            matches.append({"keyword": kw, "line": i, "snippet": line.strip()[:100]})
                            break
            if matches:
                evidence_list.append({
                    "file": path,
                    "matches": matches[:5],
                    "keyword_hit_count": len(matches),
                })

        evidence_map[req_id] = evidence_list

    return {"evidence_map": evidence_map}


# ---------------------------------------------------------------------------
# Node 3 — LLM validation (Pass 3) — can be called multiple times
# ---------------------------------------------------------------------------

async def validate_requirements(state: RequirementsGraphState) -> dict:
    requirements = state.get("parsed_requirements", [])
    evidence_map = state.get("evidence_map", {})
    all_code = state.get("all_code", "")
    retry_count = state.get("retry_count", 0)

    _emit(state, f"[graph] Pass 3: Validating requirements (attempt {retry_count + 1})...")

    if not requirements:
        return {"validation_results": [], "coverage_score": 5.0, "retry_count": retry_count + 1}

    evidence_summary = [
        {
            "id": req.get("id", ""),
            "description": req.get("description", ""),
            "evidence_files": [e["file"] for e in evidence_map.get(req.get("id", ""), [])],
            "evidence_count": sum(e["keyword_hit_count"] for e in evidence_map.get(req.get("id", ""), [])),
        }
        for req in requirements
    ]

    prompt = f"""Given these project requirements and code evidence, validate each requirement.

Requirements with evidence:
{_json_compact(evidence_summary[:15])}

Code sample (first 4000 chars):
{all_code[:4000]}

For each requirement, determine if it's implemented. Return ONLY valid JSON:
{{
  "validations": [
    {{
      "id": "REQ-001",
      "status": "implemented|partial|missing",
      "confidence": 0.0,
      "evidence_notes": "what was found",
      "gaps": ["what's missing"]
    }}
  ]
}}"""

    try:
        response = await ollama_chat(prompt, timeout=150)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, dict):
            try:
                validated_out = ValidationOutput(**parsed).model_dump()
            except Exception:
                validated_out = {"validations": []}

            validations = validated_out.get("validations", [])
            validation_by_id = {v["id"]: v for v in validations}

            results = []
            for req in requirements:
                req_id = req.get("id", "")
                val = validation_by_id.get(req_id, {})
                results.append({
                    "id": req_id,
                    "description": req.get("description", ""),
                    "priority": req.get("priority", "must"),
                    "status": val.get("status", "missing"),
                    "confidence": val.get("confidence", 0.5),
                    "evidence_notes": val.get("evidence_notes", ""),
                    "gaps": val.get("gaps", []),
                    "evidence_files": [e["file"] for e in evidence_map.get(req_id, [])],
                })

            coverage = _compute_coverage(results)
            return {
                "validation_results": results,
                "coverage_score": coverage,
                "retry_count": retry_count + 1,
            }
    except Exception as e:
        _emit(state, f"[graph] Pass 3 failed: {e}")

    # Fallback: evidence-based heuristic
    results = []
    for req in requirements:
        req_id = req.get("id", "")
        evidence = evidence_map.get(req_id, [])
        status = ("implemented" if len(evidence) >= 2
                  else "partial" if len(evidence) == 1
                  else "missing")
        results.append({
            "id": req_id,
            "description": req.get("description", ""),
            "priority": req.get("priority", "must"),
            "status": status,
            "confidence": 0.4,
            "evidence_notes": f"Found in {len(evidence)} file(s)" if evidence else "No direct evidence",
            "gaps": [],
            "evidence_files": [e["file"] for e in evidence],
        })

    coverage = _compute_coverage(results)
    return {
        "validation_results": results,
        "coverage_score": coverage,
        "retry_count": retry_count + 1,
    }


# ---------------------------------------------------------------------------
# Node 4 — Targeted retry for missing requirements (the new LangGraph value)
# ---------------------------------------------------------------------------

async def targeted_retry(state: RequirementsGraphState) -> dict:
    """
    Re-examine only the requirements marked 'missing' with a more focused
    prompt and a broader code window. Updates evidence_map with any new hits
    found via keyword expansion before re-validating.
    """
    validation_results = state.get("validation_results", [])
    evidence_map = state.get("evidence_map", {})
    all_files = state.get("all_files", {})
    all_code = state.get("all_code", "")
    retry_count = state.get("retry_count", 0)

    missing = [r for r in validation_results if r.get("status") == "missing"]
    _emit(state, f"[graph] Retry {retry_count}: re-examining {len(missing)} missing requirement(s)...")

    if not missing:
        return {}

    # Expand evidence search for missing requirements using acceptance criteria as additional keywords
    requirements = state.get("parsed_requirements", [])
    req_by_id = {r.get("id", ""): r for r in requirements}
    stop_words = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
                  "of", "is", "are", "be", "that", "this", "it", "with"}
    updated_evidence = dict(evidence_map)

    for r in missing:
        req_id = r.get("id", "")
        req = req_by_id.get(req_id, {})
        # Use acceptance criteria as additional keywords
        criteria_text = " ".join(req.get("acceptance_criteria", []))
        desc_text = f"{r.get('description', '')} {criteria_text}".lower()
        words = re.findall(r"\b[a-z]{3,}\b", desc_text)
        keywords = [w for w in words if w not in stop_words][:12]

        new_evidence = list(updated_evidence.get(req_id, []))
        seen_files = {e["file"] for e in new_evidence}

        for path, entry in all_files.items():
            if path in seen_files:
                continue
            content = entry.get("content", "") if isinstance(entry, dict) else ""
            content_lower = content.lower()
            matches = []
            for kw in keywords:
                if kw in content_lower:
                    lines = content.splitlines()
                    for i, line in enumerate(lines[:200], start=1):
                        if kw.lower() in line.lower():
                            matches.append({"keyword": kw, "line": i, "snippet": line.strip()[:100]})
                            break
            if matches:
                new_evidence.append({
                    "file": path,
                    "matches": matches[:5],
                    "keyword_hit_count": len(matches),
                })

        updated_evidence[req_id] = new_evidence

    # Focused LLM call: only the missing requirements + deeper code sample
    missing_summary = [
        {
            "id": r.get("id", ""),
            "description": r.get("description", ""),
            "evidence_files": [e["file"] for e in updated_evidence.get(r.get("id", ""), [])],
            "evidence_count": sum(
                e["keyword_hit_count"] for e in updated_evidence.get(r.get("id", ""), [])
            ),
        }
        for r in missing
    ]

    prompt = f"""You previously marked these requirements as 'missing'. Look again more carefully.
Some implementations may be implicit or use different naming conventions.

Requirements to re-examine:
{_json_compact(missing_summary)}

Full code sample (6000 chars):
{all_code[:6000]}

For each requirement, reassess. Return ONLY valid JSON:
{{
  "validations": [
    {{
      "id": "REQ-001",
      "status": "implemented|partial|missing",
      "confidence": 0.0,
      "evidence_notes": "what was found on second look",
      "gaps": []
    }}
  ]
}}"""

    try:
        response = await ollama_chat(prompt, timeout=150)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, dict):
            try:
                validated_out = ValidationOutput(**parsed).model_dump()
            except Exception:
                validated_out = {"validations": []}

            retry_by_id = {v["id"]: v for v in validated_out.get("validations", [])}

            # Merge retry results back into validation_results
            updated_results = []
            for r in validation_results:
                req_id = r.get("id", "")
                if req_id in retry_by_id:
                    retry_val = retry_by_id[req_id]
                    updated_results.append({
                        **r,
                        "status": retry_val.get("status", r.get("status")),
                        "confidence": retry_val.get("confidence", r.get("confidence")),
                        "evidence_notes": retry_val.get("evidence_notes", r.get("evidence_notes")),
                        "gaps": retry_val.get("gaps", r.get("gaps", [])),
                        "evidence_files": [e["file"] for e in updated_evidence.get(req_id, [])],
                    })
                else:
                    updated_results.append(r)

            return {
                "validation_results": updated_results,
                "evidence_map": updated_evidence,
            }
    except Exception as e:
        _emit(state, f"[graph] Targeted retry failed: {e}")

    return {"evidence_map": updated_evidence}


# ---------------------------------------------------------------------------
# Node 5 — Generate flows + test scenarios (Pass 4 + Pass 5)
# ---------------------------------------------------------------------------

async def generate_scenarios(state: RequirementsGraphState) -> dict:
    """Combined flow tracing (Pass 4) and test scenario generation (Pass 5)."""
    problem_statement = state["problem_statement"]
    requirements = state.get("parsed_requirements", [])
    validation_results = state.get("validation_results", [])
    all_code = state.get("all_code", "")

    _emit(state, "[graph] Pass 4+5: Tracing flows and generating test scenarios...")

    req_descriptions = [
        f"{r.get('id','')}: {r.get('description','')}"
        for r in requirements[:10]
    ]

    # Pass 4 — Flow tracing
    flow_prompt = f"""Trace end-to-end user flows for this application.

Problem Statement:
{problem_statement[:1000]}

Key Requirements:
{chr(10).join(req_descriptions)}

Code sample:
{all_code[:3000]}

Identify 3-5 main user flows and trace them through the code. Return ONLY valid JSON:
{{
  "flows": [
    {{
      "name": "User Authentication Flow",
      "steps": [
        {{"step": 1, "description": "User submits login form", "frontend_component": "LoginForm", "backend_endpoint": "POST /auth/login", "implemented": true}}
      ],
      "complete": true,
      "missing_steps": []
    }}
  ]
}}"""

    flow_validations: List[Dict] = []
    try:
        response = await ollama_chat(flow_prompt, timeout=150)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, dict):
            try:
                validated = FlowTracingOutput(**parsed).model_dump()
            except Exception:
                validated = {"flows": []}
            flow_validations = validated.get("flows", [])
    except Exception as e:
        _emit(state, f"[graph] Pass 4 failed: {e}")

    # Pass 5 — Test scenarios
    gaps = [r for r in validation_results if r.get("status") in ("missing", "partial")][:10]
    req_list = [f"{r.get('id','')}: {r.get('description','')}" for r in requirements[:10]]

    scenario_prompt = f"""Generate test scenarios for this application.

Requirements:
{chr(10).join(req_list)}

Missing/Partial requirements:
{chr(10).join(f"- {g.get('id','')}: {g.get('description','')}" for g in gaps) or "(none)"}

Return ONLY valid JSON:
{{
  "test_scenarios": [
    {{
      "id": "TC-001",
      "requirement_id": "REQ-001",
      "title": "Test scenario title",
      "type": "unit|integration|e2e",
      "steps": ["step 1", "step 2"],
      "expected_result": "what should happen",
      "priority": "critical|high|medium|low"
    }}
  ]
}}

Generate 5-10 test scenarios covering the most important requirements."""

    test_scenarios: List[Dict] = []
    try:
        response = await ollama_chat(scenario_prompt, timeout=120)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, dict):
            try:
                validated = TestScenariosOutput(**parsed).model_dump()
            except Exception:
                validated = {"test_scenarios": []}
            test_scenarios = validated.get("test_scenarios", [])
    except Exception as e:
        _emit(state, f"[graph] Pass 5 failed: {e}")

    return {"flow_validations": flow_validations, "test_scenarios": test_scenarios}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _should_retry(state: RequirementsGraphState) -> str:
    coverage = state.get("coverage_score", 10.0)
    retries = state.get("retry_count", 0)
    if coverage < _RETRY_COVERAGE_THRESHOLD and retries < _MAX_RETRIES:
        return "targeted_retry"
    return "generate_scenarios"


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

def _build_requirements_graph() -> Any:
    g = StateGraph(RequirementsGraphState)

    g.add_node("parse_requirements", parse_requirements)
    g.add_node("search_evidence", search_evidence)
    g.add_node("validate_requirements", validate_requirements)
    g.add_node("targeted_retry", targeted_retry)
    g.add_node("generate_scenarios", generate_scenarios)

    g.set_entry_point("parse_requirements")
    g.add_edge("parse_requirements", "search_evidence")
    g.add_edge("search_evidence", "validate_requirements")
    g.add_conditional_edges(
        "validate_requirements",
        _should_retry,
        {"targeted_retry": "targeted_retry", "generate_scenarios": "generate_scenarios"},
    )
    # After a retry, re-run validation to get updated coverage_score
    g.add_edge("targeted_retry", "validate_requirements")
    g.add_edge("generate_scenarios", END)

    return g.compile()


_requirements_graph = _build_requirements_graph()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_requirements_graph(
    problem_statement: str,
    all_files: Dict[str, Any],
    all_code: str,
    queue: Any,
    llm_context: str,
) -> Dict[str, Any]:
    """
    Run the requirements LangGraph subgraph.
    Returns a dict with the same keys that RequirementsAgent.run() expects:
      parsed_requirements, implicit_requirements, validation_results,
      flow_validations, test_scenarios, evidence_map, coverage_score
    """
    initial_state: RequirementsGraphState = {
        "problem_statement": problem_statement,
        "all_files": all_files,
        "all_code": all_code,
        "queue": queue,
        "llm_context": llm_context,
        "parsed_requirements": [],
        "implicit_requirements": [],
        "evidence_map": {},
        "validation_results": [],
        "coverage_score": 5.0,
        "retry_count": 0,
        "flow_validations": [],
        "test_scenarios": [],
    }

    result = await _requirements_graph.ainvoke(initial_state)
    return {
        "parsed_requirements": result.get("parsed_requirements", []),
        "implicit_requirements": result.get("implicit_requirements", []),
        "validation_results": result.get("validation_results", []),
        "flow_validations": result.get("flow_validations", []),
        "test_scenarios": result.get("test_scenarios", []),
        "evidence_map": result.get("evidence_map", {}),
        "coverage_score": result.get("coverage_score", 5.0),
    }
