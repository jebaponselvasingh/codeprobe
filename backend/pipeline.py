import asyncio
import json
import uuid
import shutil
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from agents.agent_01_extract import ExtractAgent
from agents.agent_02_structure import StructureAgent
from agents.agent_03_react import ReactAgent
from agents.agent_04_fastapi import FastAPIAgent
from agents.agent_05_security import SecurityAgent
from agents.agent_06_performance import PerformanceAgent
from agents.agent_07_codesmell import CodeSmellAgent
from agents.agent_08_testcoverage import TestCoverageAgent
from agents.agent_09_dependencies import DependencyAgent
from agents.agent_10_accessibility import AccessibilityAgent
from agents.agent_11_documentation import DocumentationAgent
from agents.agent_12_integration import IntegrationAgent
from agents.agent_13_requirements import RequirementsAgent
from agents.agent_14_plagiarism import PlagiarismAgent
from agents.agent_15_complexity import ComplexityAgent
from agents.agent_16_report import ReportAgent

SESSIONS_DIR = Path("./data/sessions")


async def _load_profile_config(profile_id: str, db_path: str) -> dict:
    """Load profile config from DB. Returns {} if not found."""
    try:
        import aiosqlite, json as _json
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT config_json FROM profiles WHERE id=?", (profile_id,))
            row = await cursor.fetchone()
            if row and row["config_json"]:
                return _json.loads(row["config_json"])
    except Exception:
        pass
    return {}


async def _load_rubric_config(rubric_id: str, db_path: str) -> dict:
    """Load rubric categories from DB. Returns {} if not found."""
    try:
        import aiosqlite, json as _json
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT name, categories_json FROM rubrics WHERE id=?", (rubric_id,))
            row = await cursor.fetchone()
            if row and row["categories_json"]:
                return {
                    "id": rubric_id,
                    "name": row["name"],
                    "categories": _json.loads(row["categories_json"]),
                }
    except Exception:
        pass
    return {}


async def run_agent_safe(agent, state: Dict, queue: asyncio.Queue) -> Dict:
    """Run an agent, catch exceptions, emit non-fatal error on failure."""
    try:
        return await agent.run(state, queue)
    except Exception as e:
        queue.put_nowait({
            "type": "error",
            "agent": agent.agent_id,
            "phase": agent.phase,
            "message": str(e),
            "fatal": False,
        })
        return state  # return state unchanged on failure


async def run_pipeline(
    session_id: str,
    zip_paths: Dict[str, str],
    problem_statement: Optional[str],
    profile_id: str,
    rubric_id: Optional[str] = None,
    student_name: Optional[str] = None,
    project_id: Optional[str] = None,
    queue: asyncio.Queue = None,
    db_path: str = "",
    start_time: float = 0.0,
    quick_mode: bool = False,
) -> Optional[Dict]:
    """
    Orchestrate the Phase 1 agent pipeline.
    Returns the final report dict, or None on cancellation.
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    temp_dir = SESSIONS_DIR / session_id
    temp_dir.mkdir(exist_ok=True)

    # Shared cancelled flag — a mutable list so it can be updated from outside
    cancelled_flag = [False]

    state: Dict[str, Any] = {
        "session_id": session_id,
        "temp_dir": str(temp_dir),
        "zip_paths": zip_paths,
        "problem_statement": problem_statement,
        "profile_id": profile_id,
        "student_name": student_name,
        "project_id": project_id,
        "cancelled": False,
        "_cancelled_flag": cancelled_flag,
    }

    import aiosqlite

    def is_cancelled():
        return cancelled_flag[0]

    # Load profile configuration
    profile_config = await _load_profile_config(profile_id, db_path)
    skip_agents = list(profile_config.get("skip_agents", []))
    state["profile_config"] = profile_config
    state["skip_agents"] = skip_agents
    state["quick_mode"] = quick_mode
    state["db_path"] = db_path

    # Load rubric configuration if provided
    rubric_config = {}
    if rubric_id:
        rubric_config = await _load_rubric_config(rubric_id, db_path)
    state["rubric_config"] = rubric_config

    # Quick mode: skip slow, non-essential agents
    quick_skip = []
    if quick_mode:
        quick_skip = ["plagiarism", "documentation", "accessibility", "requirements", "complexity"]

    queue.put_nowait({"type": "progress", "agent": "pipeline", "phase": 0,
                      "message": f"Profile: {profile_id}{' [quick mode]' if quick_mode else ''}, skipping: {skip_agents or 'none'}"})

    # Phase 1 — Sequential: Extract & Structure
    queue.put_nowait({"type": "progress", "agent": "extract", "phase": 1, "message": "Starting Phase 1: Setup"})

    state["_cancelled_flag"] = cancelled_flag
    state = await run_agent_safe(ExtractAgent(), state, queue)
    if is_cancelled():
        return None

    state["_cancelled_flag"] = cancelled_flag
    state = await run_agent_safe(StructureAgent(), state, queue)
    if is_cancelled():
        return None

    # Update file_count in DB
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE reviews SET file_count=?, phase='analyzing' WHERE session_id=?",
            (state.get("file_count", 0), session_id)
        )
        await db.commit()

    # Phase 2 — Parallel fan-out (agents 3, 4, 12)
    queue.put_nowait({"type": "progress", "agent": "react", "phase": 2, "message": "Starting Phase 2: Deep Analysis (parallel)"})

    # Each parallel agent gets a copy of shared state plus the cancelled flag
    state_for_parallel = {**state, "_cancelled_flag": cancelled_flag}

    # Build list of agents to run (respecting skip_agents from profile)
    parallel_agents = [
        (ReactAgent(),        "react"),
        (FastAPIAgent(),      "fastapi"),
        (IntegrationAgent(),  "integration"),
        (SecurityAgent(),     "security"),
        (CodeSmellAgent(),    "codesmell"),
        (ComplexityAgent(),   "complexity"),
        (PerformanceAgent(),  "performance"),
        (TestCoverageAgent(), "testcoverage"),
        (DependencyAgent(),   "dependencies"),
        (AccessibilityAgent(), "accessibility"),
        (DocumentationAgent(), "documentation"),
    ]

    active_agents = [
        (agent, aid) for agent, aid in parallel_agents
        if aid not in skip_agents and aid not in quick_skip
    ]

    results = await asyncio.gather(
        *[run_agent_safe(agent, {**state_for_parallel}, queue) for agent, _ in active_agents],
        return_exceptions=False,
    )

    # Merge all parallel results back into state
    for r in results:
        if isinstance(r, dict):
            # Only merge agent-specific output keys, not overwrite shared input keys
            for k, v in r.items():
                if k not in ("zip_paths", "temp_dir", "session_id", "_cancelled_flag"):
                    state[k] = v

    # Restore cancelled flag after merge
    state["_cancelled_flag"] = cancelled_flag

    if is_cancelled():
        return None

    # Phase 3 — Requirements & Plagiarism (conditional, skipped in quick_mode)
    queue.put_nowait({"type": "progress", "agent": "requirements", "phase": 3, "message": "Starting Phase 3: Cross-Analysis"})

    if "requirements" not in skip_agents and "requirements" not in quick_skip:
        state["_cancelled_flag"] = cancelled_flag
        state = await run_agent_safe(RequirementsAgent(), state, queue)
        if is_cancelled():
            return None

    if "plagiarism" not in skip_agents and "plagiarism" not in quick_skip:
        state["_cancelled_flag"] = cancelled_flag
        state = await run_agent_safe(PlagiarismAgent(), state, queue)
        if is_cancelled():
            return None

    # Phase 4 — Report
    queue.put_nowait({"type": "progress", "agent": "report", "phase": 4, "message": "Generating final report..."})
    state["_start_time"] = start_time
    state["_cancelled_flag"] = cancelled_flag
    state = await run_agent_safe(ReportAgent(), state, queue)

    report = state.get("report")

    # Persist report to DB
    if report:
        import json as _json
        overall = report.get("scores", {}).get("overall", 0)
        grade = report.get("scores", {}).get("grade", "F")
        cat_scores = _json.dumps(report.get("scores", {}).get("categories", {}))
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """UPDATE reviews SET overall_score=?, grade=?, category_scores_json=?,
                   report_json=?, phase='complete' WHERE session_id=?""",
                (overall, grade, cat_scores, _json.dumps(report), session_id)
            )
            await db.commit()

    queue.put_nowait({"type": "complete"})

    # Schedule temp dir cleanup after 5 minutes (keep for file serving)
    async def cleanup():
        await asyncio.sleep(300)
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    asyncio.create_task(cleanup())

    return report
