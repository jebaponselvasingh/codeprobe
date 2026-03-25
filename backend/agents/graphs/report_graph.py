"""
LangGraph subgraph for ReportAgent — iterative critic refinement.

Flow:
  run_initial_critique
         |
  check_removal_rate ── (≤ 70% removed) ──► apply_results ──► END
         |
  (> 70% removed — over-filtered)
         |
  refine_critique
         |
  apply_results ──► END

Value over single-pass:
  - If the critic removes an unusually high fraction of findings (> 70%),
    a refinement pass is run with a stricter prompt that instructs the LLM
    to be more conservative, protecting against over-aggressive filtering.
  - The final applied set is always bounded: at most 70% of findings can
    be removed regardless of what the LLM returns.
"""

import json
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from utils.ollama import ollama_chat, parse_llm_json


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class ReportGraphState(TypedDict):
    # Inputs
    findings: List[Dict]           # full findings list from all agents
    strictness: str                # "strict" | "moderate" | "lenient"
    queue: Any                     # asyncio.Queue — opaque
    # Intermediate
    candidates: List[Dict]         # subset sent to LLM (errors + warnings, ≤ 20)
    critique_result: List[Dict]    # raw LLM output [{i, false_positive}]
    fp_indices: List[int]          # confirmed false-positive indices
    removal_rate: float            # fraction removed (0.0–1.0)
    # Output
    filtered_findings: List[Dict]  # final deduplicated findings


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _emit(state: ReportGraphState, msg: str) -> None:
    q = state.get("queue")
    if q is not None:
        try:
            q.put_nowait({"type": "progress", "agent": "report", "phase": 4, "message": msg})
        except Exception:
            pass


def _build_compact(candidates: List[Dict]) -> str:
    return json.dumps(
        [
            {
                "i": i,
                "type": f.get("type"),
                "area": f.get("area"),
                "detail": f.get("detail"),
                "file": f.get("file"),
            }
            for i, f in enumerate(candidates)
        ],
        separators=(",", ":"),
    )[:3000]


def _parse_fp_indices(parsed: Any, n_candidates: int) -> List[int]:
    """Extract false-positive indices from LLM JSON list."""
    if not parsed or not isinstance(parsed, list):
        return []
    return [
        item["i"]
        for item in parsed
        if isinstance(item, dict)
        and item.get("false_positive")
        and isinstance(item.get("i"), int)
        and 0 <= item["i"] < n_candidates
    ]


# ---------------------------------------------------------------------------
# Node 1 — Select candidates and run initial critique
# ---------------------------------------------------------------------------

async def run_initial_critique(state: ReportGraphState) -> dict:
    """Select error/warning findings and ask LLM to mark false positives."""
    findings = state.get("findings", [])
    strictness = state.get("strictness", "moderate")

    candidates = [f for f in findings if f.get("type") in ("error", "warning")][:20]
    if not candidates:
        return {
            "candidates": [],
            "critique_result": [],
            "fp_indices": [],
            "removal_rate": 0.0,
        }

    _emit(state, f"[graph] Critic pass: reviewing {len(candidates)} finding(s) for false positives...")

    compact = _build_compact(candidates)

    prompt = (
        f"You are a senior code reviewer validating automated findings.\n"
        f"Review strictness: {strictness}.\n\n"
        "Below are automated findings. Mark any that are CLEARLY false positives "
        "(e.g. triggered by variable names, test code, framework boilerplate) with false_positive=true.\n\n"
        f"Findings:\n{compact}\n\n"
        "Return ONLY valid JSON:\n"
        f'[{{"i": 0, "false_positive": false}}, ...]\n'
        f"Include ALL {len(candidates)} entries in the same order."
    )

    try:
        response = await ollama_chat(prompt, timeout=120)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, list) and len(parsed) >= len(candidates) // 2:
            fp_indices = _parse_fp_indices(parsed, len(candidates))
            removal_rate = len(fp_indices) / len(candidates) if candidates else 0.0
            return {
                "candidates": candidates,
                "critique_result": parsed,
                "fp_indices": fp_indices,
                "removal_rate": removal_rate,
            }
    except Exception as e:
        _emit(state, f"[graph] Initial critique failed: {e}")

    return {
        "candidates": candidates,
        "critique_result": [],
        "fp_indices": [],
        "removal_rate": 0.0,
    }


# ---------------------------------------------------------------------------
# Node 2 — Refine critique (only when over-filtered)
# ---------------------------------------------------------------------------

async def refine_critique(state: ReportGraphState) -> dict:
    """Re-run with a conservative prompt when > 70% of findings were removed."""
    candidates = state.get("candidates", [])
    fp_indices = state.get("fp_indices", [])

    _emit(
        state,
        f"[graph] Over-filtered ({len(fp_indices)}/{len(candidates)} removed) — refining critique..."
    )

    # Only challenge the flagged items
    flagged = [{"i": i, **candidates[i]} for i in fp_indices if i < len(candidates)]
    compact = json.dumps(
        [{"i": f["i"], "detail": f.get("detail", ""), "file": f.get("file", "")} for f in flagged],
        separators=(",", ":"),
    )[:2000]

    prompt = (
        "You previously marked many findings as false positives. Re-examine these specific items more carefully.\n"
        "Only mark as false_positive=true if you are VERY CERTAIN it is not a real issue.\n"
        "When in doubt, keep the finding (false_positive=false).\n\n"
        f"Re-examine:\n{compact}\n\n"
        "Return ONLY valid JSON — same format:\n"
        '[{"i": <original index>, "false_positive": false}, ...]'
    )

    try:
        response = await ollama_chat(prompt, timeout=90)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, list):
            refined_fp = _parse_fp_indices(parsed, len(candidates))
            # Intersect: only keep confirmed FPs from the refinement
            confirmed_fp = [i for i in fp_indices if i in set(refined_fp)]
            removal_rate = len(confirmed_fp) / len(candidates) if candidates else 0.0
            return {"fp_indices": confirmed_fp, "removal_rate": removal_rate}
    except Exception as e:
        _emit(state, f"[graph] Refinement failed: {e}")

    # If refinement fails, cap removal at 50%
    max_removals = max(0, len(candidates) // 2)
    capped = fp_indices[:max_removals]
    return {"fp_indices": capped, "removal_rate": len(capped) / len(candidates) if candidates else 0.0}


# ---------------------------------------------------------------------------
# Node 3 — Apply results
# ---------------------------------------------------------------------------

def apply_results(state: ReportGraphState) -> dict:
    """Remove confirmed false positives from the findings list."""
    findings = state.get("findings", [])
    candidates = state.get("candidates", [])
    fp_indices = state.get("fp_indices", [])

    if not candidates or not fp_indices:
        return {"filtered_findings": findings}

    # Safety cap: never remove more than 70% of candidates
    max_removals = int(len(candidates) * 0.7)
    capped_fp = set(fp_indices[:max_removals])

    # Map candidates back to their positions in the full findings list
    candidate_details = {
        (c.get("file", ""), c.get("detail", "")[:40])
        for i, c in enumerate(candidates)
        if i in capped_fp
    }

    filtered = [
        f for f in findings
        if (f.get("file", ""), f.get("detail", "")[:40]) not in candidate_details
    ]

    removed = len(findings) - len(filtered)
    if removed:
        _emit(state, f"[graph] Critic removed {removed} false positive(s) from findings")

    return {"filtered_findings": filtered}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_after_critique(state: ReportGraphState) -> str:
    return "refine_critique" if state.get("removal_rate", 0.0) > 0.70 else "apply_results"


# ---------------------------------------------------------------------------
# Build & compile graph (once at import time)
# ---------------------------------------------------------------------------

def _build_report_graph():
    g = StateGraph(ReportGraphState)

    g.add_node("run_initial_critique", run_initial_critique)
    g.add_node("refine_critique", refine_critique)
    g.add_node("apply_results", apply_results)

    g.set_entry_point("run_initial_critique")
    g.add_conditional_edges(
        "run_initial_critique",
        _route_after_critique,
        {"refine_critique": "refine_critique", "apply_results": "apply_results"},
    )
    g.add_edge("refine_critique", "apply_results")
    g.add_edge("apply_results", END)

    return g.compile()


_report_graph = _build_report_graph()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_report_graph(
    findings: List[Dict],
    strictness: str,
    queue: Any,
) -> List[Dict]:
    """
    Run the report critic LangGraph subgraph.
    Returns the filtered findings list with confirmed false positives removed.
    """
    initial_state: ReportGraphState = {
        "findings": findings,
        "strictness": strictness,
        "queue": queue,
        "candidates": [],
        "critique_result": [],
        "fp_indices": [],
        "removal_rate": 0.0,
        "filtered_findings": [],
    }

    result = await _report_graph.ainvoke(initial_state)
    return result.get("filtered_findings", findings)
