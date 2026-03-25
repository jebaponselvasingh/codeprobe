"""
LangGraph subgraph for PlagiarismAgent — confidence-gated second-opinion analysis.

Flow:
  build_excerpts
       |
  first_analysis
       |
  check_confidence ──── (confidence ≥ 60) ───► finalize ──► END
       |
  (confidence < 60)
       |
  second_opinion
       |
  finalize ──► END

Value over single-pass:
  - If the LLM is uncertain (low confidence), a second opinion with a
    different prompt angle (tutorial-pattern focus) is obtained.
  - Estimates are averaged to reduce bias in either direction.
  - Signals from both passes are merged for a richer signal set.
"""

import os
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from utils.ollama import ollama_chat, parse_llm_json


# ---------------------------------------------------------------------------
# Boilerplate registry (mirrors agent_14 constant — no import to avoid cycles)
# ---------------------------------------------------------------------------

_BOILERPLATE_KEYS = {
    "App.tsx", "App.css", "index.tsx", "reportWebVitals",
    "setupTests", "vite-env.d.ts", "main.tsx",
}


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class PlagiarismGraphState(TypedDict):
    # Inputs (set once at invocation)
    frontend_files: Dict[str, Any]
    backend_files: Dict[str, Any]
    queue: Any                     # asyncio.Queue — opaque
    llm_context: str
    # Intermediate
    file_excerpts: str
    first_pass_result: Dict
    confidence_score: float        # 0–100; gate for second opinion
    second_pass_result: Dict
    # Output
    final_result: Dict


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _emit(state: PlagiarismGraphState, msg: str) -> None:
    q = state.get("queue")
    if q is not None:
        try:
            q.put_nowait({"type": "progress", "agent": "plagiarism", "phase": 3, "message": msg})
        except Exception:
            pass


def _is_boilerplate(path: str) -> bool:
    basename = os.path.basename(path)
    basename_no_ext = os.path.splitext(basename)[0]
    return any(
        basename == key or basename_no_ext == key or basename.startswith(key)
        for key in _BOILERPLATE_KEYS
    )


# ---------------------------------------------------------------------------
# Node 1 — Build excerpts (pure Python)
# ---------------------------------------------------------------------------

def build_excerpts(state: PlagiarismGraphState) -> dict:
    """Select non-boilerplate files and build an LLM-ready excerpt string."""
    frontend_files = state.get("frontend_files", {})
    backend_files = state.get("backend_files", {})

    def _size(item):
        path, entry = item
        content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
        return len(content)

    fe_non_bp = [(p, e) for p, e in frontend_files.items() if not _is_boilerplate(p)]
    fe_non_bp.sort(key=_size, reverse=True)

    be_items = sorted(backend_files.items(), key=_size, reverse=True)

    parts = []
    for path, entry in fe_non_bp[:5] + be_items[:3]:
        content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
        parts.append(f"=== {path} ===\n{content[:1500]}")

    return {"file_excerpts": "\n\n".join(parts)}


# ---------------------------------------------------------------------------
# Node 2 — First LLM analysis
# ---------------------------------------------------------------------------

async def first_analysis(state: PlagiarismGraphState) -> dict:
    """First LLM pass: broad originality assessment with self-reported confidence."""
    file_excerpts = state.get("file_excerpts", "")
    if not file_excerpts.strip():
        return {"first_pass_result": {}, "confidence_score": 100.0}

    _emit(state, "[graph] Running first-pass originality analysis...")

    llm_context = state.get("llm_context", "")
    context_prefix = f"{llm_context}\n\n" if llm_context else ""

    prompt = (
        f"{context_prefix}"
        "Review these code files from a student project submission.\n\n"
        f"Files:\n{file_excerpts}\n\n"
        "Assess:\n"
        "1. Does this appear to be mostly original student work or copy-pasted tutorials?\n"
        "2. What percentage appears original (estimate 0-100)?\n"
        "3. What tutorial patterns or boilerplate do you see?\n"
        "4. What signs of genuine effort or original implementation exist?\n"
        "5. How confident are you in this assessment (0-100)?\n\n"
        "Return ONLY valid JSON:\n"
        '{"originality_estimate": <0-100 integer>, "assessment": "<2-3 sentence summary>", '
        '"tutorial_signals": ["<signal1>"], "original_elements": ["<element1>"], '
        '"confidence": <0-100 integer>}'
    )

    try:
        response = await ollama_chat(prompt, timeout=180)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, dict):
            confidence = float(parsed.get("confidence", 70))
            return {"first_pass_result": parsed, "confidence_score": confidence}
    except Exception as e:
        _emit(state, f"[graph] First-pass failed: {e}")

    return {"first_pass_result": {}, "confidence_score": 100.0}


# ---------------------------------------------------------------------------
# Node 3 — Second opinion (only when confidence < 60)
# ---------------------------------------------------------------------------

async def second_opinion(state: PlagiarismGraphState) -> dict:
    """Second LLM pass with a tutorial-pattern-focused prompt for low-confidence cases."""
    file_excerpts = state.get("file_excerpts", "")
    first_result = state.get("first_pass_result", {})

    _emit(state, f"[graph] Confidence {state.get('confidence_score', 0):.0f}% — running second-opinion analysis...")

    prompt = (
        "You are reviewing a student code submission for originality. "
        "A first review had low confidence. Focus specifically on identifying:\n"
        "- Direct tutorial code (React Todo, FastAPI Todo, JSONPlaceholder examples)\n"
        "- Variable names copied from documentation examples\n"
        "- Structural patterns that match common tutorial templates\n\n"
        f"Files:\n{file_excerpts[:3000]}\n\n"
        f"First review estimated originality at: {first_result.get('originality_estimate', 'unknown')}%\n\n"
        "Return ONLY valid JSON:\n"
        '{"originality_estimate": <0-100 integer>, "assessment": "<2-3 sentence summary>", '
        '"tutorial_signals": ["<signal1>"], "original_elements": ["<element1>"]}'
    )

    try:
        response = await ollama_chat(prompt, timeout=120)
        parsed = parse_llm_json(response, default=None)
        if parsed and isinstance(parsed, dict):
            return {"second_pass_result": parsed}
    except Exception as e:
        _emit(state, f"[graph] Second-opinion failed: {e}")

    return {"second_pass_result": {}}


# ---------------------------------------------------------------------------
# Node 4 — Finalize (merge passes)
# ---------------------------------------------------------------------------

def finalize(state: PlagiarismGraphState) -> dict:
    """Merge first and (optional) second-pass results into final_result."""
    first = state.get("first_pass_result", {})
    second = state.get("second_pass_result", {})

    if second:
        est1 = float(first.get("originality_estimate", 50))
        est2 = float(second.get("originality_estimate", 50))
        originality_estimate = round((est1 + est2) / 2)

        # Merge and deduplicate preserving order
        signals = list(dict.fromkeys(
            (first.get("tutorial_signals") or []) + (second.get("tutorial_signals") or [])
        ))
        elements = list(dict.fromkeys(
            (first.get("original_elements") or []) + (second.get("original_elements") or [])
        ))
        assessment = second.get("assessment") or first.get("assessment") or ""
    else:
        originality_estimate = int(first.get("originality_estimate", 50))
        signals = first.get("tutorial_signals") or []
        elements = first.get("original_elements") or []
        assessment = first.get("assessment") or ""

    return {
        "final_result": {
            "originality_estimate": originality_estimate,
            "assessment": assessment,
            "tutorial_signals": signals,
            "original_elements": elements,
        }
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_after_first(state: PlagiarismGraphState) -> str:
    return "second_opinion" if state.get("confidence_score", 100.0) < 60.0 else "finalize"


# ---------------------------------------------------------------------------
# Build & compile graph (once at import time)
# ---------------------------------------------------------------------------

def _build_plagiarism_graph():
    g = StateGraph(PlagiarismGraphState)

    g.add_node("build_excerpts", build_excerpts)
    g.add_node("first_analysis", first_analysis)
    g.add_node("second_opinion", second_opinion)
    g.add_node("finalize", finalize)

    g.set_entry_point("build_excerpts")
    g.add_edge("build_excerpts", "first_analysis")
    g.add_conditional_edges(
        "first_analysis",
        _route_after_first,
        {"second_opinion": "second_opinion", "finalize": "finalize"},
    )
    g.add_edge("second_opinion", "finalize")
    g.add_edge("finalize", END)

    return g.compile()


_plagiarism_graph = _build_plagiarism_graph()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_plagiarism_graph(
    frontend_files: Dict[str, Any],
    backend_files: Dict[str, Any],
    queue: Any,
    llm_context: str,
) -> Dict:
    """
    Run the plagiarism LangGraph subgraph.
    Returns a dict with keys: originality_estimate, assessment,
    tutorial_signals, original_elements — matching PlagiarismLLMOutput fields.
    """
    initial_state: PlagiarismGraphState = {
        "frontend_files": frontend_files,
        "backend_files": backend_files,
        "queue": queue,
        "llm_context": llm_context,
        "file_excerpts": "",
        "first_pass_result": {},
        "confidence_score": 100.0,
        "second_pass_result": {},
        "final_result": {},
    }

    result = await _plagiarism_graph.ainvoke(initial_state)
    return result.get("final_result", {})
