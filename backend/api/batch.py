import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import aiosqlite
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from database import DB_PATH
from pipeline import run_pipeline, SESSIONS_DIR

router = APIRouter()

# batch_id -> { queue: asyncio.Queue, tasks: list }
_batch_sessions: Dict[str, dict] = {}


@router.post("/review/batch")
async def start_batch_review(
    zips: List[UploadFile] = File(...),
    student_names: str = Form(""),
    problem_statement: Optional[str] = Form(None),
    profile_id: str = Form("bootcamp"),
    rubric_id: Optional[str] = Form(None),
    concurrency_limit: int = Form(3),
):
    try:
        names = json.loads(student_names) if student_names.strip() else []
    except Exception:
        names = []
    while len(names) < len(zips):
        names.append(f"Student {len(names) + 1}")

    batch_id = str(uuid.uuid4())
    batch_dir = SESSIONS_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    batch_queue: asyncio.Queue = asyncio.Queue()
    semaphore = asyncio.Semaphore(concurrency_limit)
    tasks = []
    student_sessions = []

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO batch_reviews (id, profile_id, rubric_id, problem_statement, student_count) VALUES (?,?,?,?,?)",
            (batch_id, profile_id, rubric_id, problem_statement, len(zips))
        )

        for i, (zip_file, name) in enumerate(zip(zips, names)):
            session_id = str(uuid.uuid4())
            student_dir = batch_dir / f"student_{i}"
            student_dir.mkdir(exist_ok=True)

            zip_path = student_dir / zip_file.filename
            content = await zip_file.read()
            zip_path.write_bytes(content)

            await db.execute(
                """INSERT INTO reviews (id, session_id, student_name, profile_id, rubric_id, problem_statement, phase)
                   VALUES (?,?,?,?,?,?,'reviewing')""",
                (session_id, session_id, name, profile_id, rubric_id, problem_statement)
            )
            await db.execute(
                "INSERT INTO batch_members (batch_id, review_id, student_name, student_index) VALUES (?,?,?,?)",
                (batch_id, session_id, name, i)
            )
            student_sessions.append({
                "session_id": session_id,
                "name": name,
                "zip_path": str(zip_path),
                "index": i,
            })

        await db.commit()

    _batch_sessions[batch_id] = {"queue": batch_queue, "tasks": tasks}

    async def run_student(sess):
        async with semaphore:
            wrapped_queue: asyncio.Queue = asyncio.Queue()

            async def forwarder():
                while True:
                    event = await wrapped_queue.get()
                    tagged = {**event, "student_index": sess["index"], "student_name": sess["name"]}
                    batch_queue.put_nowait(tagged)
                    if event.get("type") == "complete":
                        break
                    if event.get("type") == "error" and event.get("fatal"):
                        break

            fwd_task = asyncio.create_task(forwarder())
            try:
                await run_pipeline(
                    session_id=sess["session_id"],
                    zip_paths={"combined": sess["zip_path"]},
                    problem_statement=problem_statement,
                    profile_id=profile_id,
                    student_name=sess["name"],
                    project_id=None,
                    queue=wrapped_queue,
                    db_path=str(DB_PATH),
                    start_time=time.time(),
                )
            except Exception as e:
                wrapped_queue.put_nowait({"type": "error", "message": str(e), "fatal": True})
            await fwd_task

    async def run_all():
        student_tasks = [asyncio.create_task(run_student(s)) for s in student_sessions]
        await asyncio.gather(*student_tasks, return_exceptions=True)
        batch_queue.put_nowait({"type": "batch_complete"})
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE batch_reviews SET status='complete' WHERE id=?", (batch_id,))
            await db.commit()

    asyncio.create_task(run_all())

    return {"batch_id": batch_id, "student_count": len(zips)}


@router.get("/review/batch/{batch_id}/stream")
async def stream_batch(batch_id: str):
    session = _batch_sessions.get(batch_id)
    if not session:
        raise HTTPException(404, "Batch session not found")

    queue = session["queue"]

    async def event_gen():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                yield 'data: {"type":"ping"}\n\n'
                continue
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "batch_complete":
                break

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/review/batch/{batch_id}/comparison")
async def get_batch_comparison(batch_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """SELECT bm.student_name, bm.student_index, r.overall_score, r.grade,
                      r.category_scores_json, r.report_json
               FROM batch_members bm
               JOIN reviews r ON bm.review_id = r.session_id
               WHERE bm.batch_id = ?
               ORDER BY bm.student_index""",
            (batch_id,)
        )
        rows = [dict(r) for r in await cursor.fetchall()]

    if not rows:
        raise HTTPException(404, "Batch not found or no results yet")

    students = []
    all_scores = []
    category_totals: dict = {}
    category_counts: dict = {}
    all_findings_by_student = []

    for row in rows:
        score = row["overall_score"] or 0
        cat_scores = json.loads(row["category_scores_json"] or "{}")
        report = json.loads(row["report_json"] or "{}")

        critical_count = len((report.get("findings") or {}).get("critical", []))

        students.append({
            "name": row["student_name"],
            "overall_score": score,
            "grade": row["grade"] or "F",
            "category_scores": cat_scores,
            "critical_count": critical_count,
        })
        all_scores.append(score)

        for cat, val in cat_scores.items():
            cat_score = val["score"] if isinstance(val, dict) else float(val)
            category_totals[cat] = category_totals.get(cat, 0) + cat_score
            category_counts[cat] = category_counts.get(cat, 0) + 1

        findings = (report.get("findings") or {}).get("critical", [])
        all_findings_by_student.append([f.get("message", "") for f in findings])

    import statistics
    from collections import Counter

    n = len(all_scores)
    mean = round(statistics.mean(all_scores), 2) if all_scores else 0
    median = round(statistics.median(all_scores), 2) if all_scores else 0
    std_dev = round(statistics.stdev(all_scores), 2) if n > 1 else 0

    per_category = {
        cat: round(category_totals[cat] / category_counts[cat], 2)
        for cat in category_totals
    }

    all_msgs = [msg for student_msgs in all_findings_by_student for msg in student_msgs]
    msg_counts = Counter(all_msgs)
    threshold = max(1, n * 0.5)
    common_issues = [
        {"issue": msg, "frequency": count, "affected_students": count}
        for msg, count in msg_counts.most_common(10)
        if count >= threshold
    ]

    sorted_scores = sorted(all_scores)
    percentile_ranks = {}
    for s in students:
        rank = sorted_scores.index(s["overall_score"])
        percentile_ranks[s["name"]] = round((rank / max(1, n - 1)) * 100)

    return {
        "batch_id": batch_id,
        "students": students,
        "class_stats": {"mean": mean, "median": median, "std_dev": std_dev, "per_category": per_category},
        "common_issues": common_issues,
        "percentile_ranks": percentile_ranks,
    }
