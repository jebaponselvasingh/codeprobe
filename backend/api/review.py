import asyncio
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

import aiosqlite
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import DB_PATH, get_db
from pipeline import run_pipeline, SESSIONS_DIR
from utils.ollama import OLLAMA_BASE_URL, OLLAMA_MODEL
from guardrails.sanitizer import sanitize_input_field

router = APIRouter()

# In-memory session registry
# Maps session_id -> {"queue": asyncio.Queue, "task": asyncio.Task, "cancelled_flag": [bool]}
_sessions: Dict[str, dict] = {}

# In-memory fix suggestion cache keyed by finding_id
_fix_cache: Dict[str, Dict] = {}


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class FixSuggestionRequest(BaseModel):
    finding_id: str
    file: str
    line: int = 0
    code_snippet: str
    description: str


@router.post("/review")
async def start_review(
    background_tasks: BackgroundTasks,
    frontend_zip: Optional[UploadFile] = File(None),
    backend_zip: Optional[UploadFile] = File(None),
    combined_zip: Optional[UploadFile] = File(None),
    problem_statement: Optional[str] = Form(None),
    profile_id: str = Form("bootcamp"),
    rubric_id: Optional[str] = Form(None),
    student_name: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    quick_mode: bool = Form(False),
):
    if not any([frontend_zip, backend_zip, combined_zip]):
        raise HTTPException(400, "At least one zip file is required")

    # Sanitize user-supplied text fields before storing or passing downstream
    student_name = sanitize_input_field(student_name or "", max_len=200) or None
    project_id = sanitize_input_field(project_id or "", max_len=100) or None
    problem_statement = sanitize_input_field(problem_statement or "", max_len=5000) or None

    session_id = str(uuid.uuid4())
    session_dir = SESSIONS_DIR / session_id / "uploads"
    session_dir.mkdir(parents=True, exist_ok=True)

    zip_paths = {}
    for field_name, upload in [("combined", combined_zip), ("frontend", frontend_zip), ("backend", backend_zip)]:
        if upload is not None:
            dest = session_dir / f"{field_name}_{upload.filename}"
            content = await upload.read()
            dest.write_bytes(content)
            zip_paths[field_name] = str(dest)

    # Determine version for re-review
    version = 1
    if project_id and student_name:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT MAX(version) as max_v FROM reviews WHERE project_id=? AND student_name=?",
                (project_id, student_name)
            )
            row = await cursor.fetchone()
            if row and row["max_v"]:
                version = row["max_v"] + 1

    # Insert review record
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO reviews (id, session_id, project_id, student_name, version,
               profile_id, rubric_id, problem_statement, phase)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'reviewing')""",
            (session_id, session_id, project_id, student_name, version,
             profile_id, rubric_id, problem_statement)
        )
        await db.commit()

    # Set up SSE queue and cancelled flag
    queue: asyncio.Queue = asyncio.Queue()
    cancelled_flag = [False]
    _sessions[session_id] = {
        "queue": queue,
        "cancelled_flag": cancelled_flag,
    }

    start_time = time.time()

    async def run_bg():
        try:
            await run_pipeline(
                session_id=session_id,
                zip_paths=zip_paths,
                problem_statement=problem_statement,
                profile_id=profile_id,
                rubric_id=rubric_id,
                student_name=student_name,
                project_id=project_id,
                queue=queue,
                db_path=str(DB_PATH),
                start_time=start_time,
                quick_mode=quick_mode,
            )
        except Exception as e:
            queue.put_nowait({"type": "error", "message": str(e), "fatal": True})
        finally:
            _sessions.pop(session_id, None)

    task = asyncio.create_task(run_bg())
    _sessions[session_id]["task"] = task

    return {"session_id": session_id, "file_count": 0}


@router.get("/review/{session_id}/stream")
async def stream_review(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        # Session not found or already complete
        raise HTTPException(404, "Session not found or already complete")

    queue: asyncio.Queue = session["queue"]

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                yield "data: {\"type\": \"ping\"}\n\n"
                continue

            yield f"data: {json.dumps(event)}\n\n"

            if event.get("type") == "complete":
                break
            if event.get("type") == "error" and event.get("fatal"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/review/{session_id}/report")
async def get_report(session_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT report_json, phase FROM reviews WHERE session_id=?", (session_id,)
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(404, "Review not found")
    if not row["report_json"]:
        raise HTTPException(202, "Review still in progress")

    return json.loads(row["report_json"])


@router.get("/review/{session_id}/file/{file_path:path}")
async def get_file(session_id: str, file_path: str):
    base = SESSIONS_DIR / session_id / "files"
    full_path = (base / file_path).resolve()

    # Security: ensure path stays within session dir
    if not str(full_path).startswith(str(base.resolve())):
        raise HTTPException(403, "Path traversal not allowed")
    if not full_path.exists():
        raise HTTPException(404, "File not found")

    content = full_path.read_text(encoding="utf-8", errors="ignore")
    ext = full_path.suffix.lower()
    lang_map = {
        ".py": "python", ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript", ".css": "css",
        ".html": "html", ".json": "json", ".md": "markdown",
        ".yaml": "yaml", ".yml": "yaml",
    }
    language = lang_map.get(ext, "text")

    return {
        "content": content,
        "language": language,
        "line_count": content.count("\n") + 1,
    }


@router.post("/review/{session_id}/cancel")
async def cancel_review(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    # Signal cancellation via the shared flag
    session["cancelled_flag"][0] = True

    # Cancel the asyncio task
    if task := session.get("task"):
        task.cancel()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE reviews SET phase='cancelled', cancelled=1 WHERE session_id=?",
            (session_id,)
        )
        await db.commit()

    session["queue"].put_nowait({"type": "complete"})
    return {"ok": True}


@router.get("/history/{project_id}")
async def get_history(
    project_id: str,
    page: int = 1,
    limit: int = 20,
    student_name: Optional[str] = None,
    sort: str = "created_at_desc",
):
    offset = (page - 1) * limit
    order = "created_at DESC" if sort == "created_at_desc" else "created_at ASC"

    where = "project_id=?"
    params: list = [project_id]
    if student_name:
        where += " AND student_name=?"
        params.append(student_name)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"SELECT COUNT(*) as total FROM reviews WHERE {where}", params
        )
        total_row = await cursor.fetchone()
        total = total_row["total"] if total_row else 0

        cursor = await db.execute(
            f"""SELECT session_id as review_id, version, overall_score, grade, created_at
                FROM reviews WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?""",
            params + [limit, offset]
        )
        items = [dict(row) for row in await cursor.fetchall()]

    return {"items": items, "total": total, "page": page, "limit": limit}


@router.delete("/history/{review_id}")
async def delete_history(review_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM chat_messages WHERE session_id=?", (review_id,))
        await db.execute("DELETE FROM reviews WHERE session_id=?", (review_id,))
        await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Streaming helper
# ---------------------------------------------------------------------------

async def _stream_ollama_chat(system: str, messages: list) -> AsyncGenerator[str, None]:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as resp:
            async for line in resp.aiter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            break
                    except Exception:
                        continue


# ---------------------------------------------------------------------------
# POST /review/{session_id}/chat
# ---------------------------------------------------------------------------

@router.post("/review/{session_id}/chat")
async def chat_with_review(session_id: str, req: ChatRequest):
    # Load report from DB
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT report_json FROM reviews WHERE session_id=?", (session_id,)
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(404, "Review not found")
    if not row["report_json"]:
        raise HTTPException(202, "Review still in progress")

    report = json.loads(row["report_json"])

    # Load last 10 chat messages for context
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT role, content FROM chat_messages WHERE session_id=? ORDER BY created_at DESC LIMIT 10",
            (session_id,)
        )
        db_messages = list(reversed(await cursor.fetchall()))

    # Build system prompt
    scores = report.get("scores", {})
    overall_score = scores.get("overall", 0)
    grade = scores.get("grade", "N/A")
    categories = scores.get("categories", {})

    findings = report.get("findings", {})
    critical = findings.get("critical", [])
    top_issues = "; ".join(f.get("detail", "") for f in critical[:3] if f.get("detail"))

    cat_summary = ", ".join(
        f"{cat}: {v.get('score', 0)}/10"
        for cat, v in categories.items()
    )

    report_json_str = json.dumps(report, indent=2)[:8000]

    system_prompt = (
        f"You are a helpful code review assistant. You have access to a detailed code review report for this student's project.\n\n"
        f"Report Summary:\n"
        f"- Overall Score: {overall_score}/10 (Grade: {grade})\n"
        f"- Key Issues: {top_issues or 'None'}\n"
        f"- Category Scores: {cat_summary}\n\n"
        f"Full Report Data:\n{report_json_str}\n\n"
        f"Help the student understand their review, explain findings, and suggest improvements. Be constructive and educational."
    )

    # Build messages list from DB history + request history + new message
    history_messages = [{"role": row["role"], "content": row["content"]} for row in db_messages]
    request_history = [{"role": m.role, "content": m.content} for m in req.history]
    all_messages = history_messages + request_history + [{"role": "user", "content": req.message}]

    # Save user message to DB
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, "user", req.message)
        )
        await db.commit()

    # Stream response
    full_response_parts: List[str] = []

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for token in _stream_ollama_chat(system_prompt, all_messages):
                full_response_parts.append(token)
                payload_str = json.dumps({"type": "token", "content": token})
                yield f"data: {payload_str}\n\n"
        except Exception:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Ollama not available'})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        # Save assistant response to DB after streaming
        full_response = "".join(full_response_parts)
        if full_response:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
                    (session_id, "assistant", full_response)
                )
                await db.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# POST /review/{session_id}/fix-suggestion
# ---------------------------------------------------------------------------

@router.post("/review/{session_id}/fix-suggestion")
async def fix_suggestion(session_id: str, req: FixSuggestionRequest):
    # Check cache first
    cached = _fix_cache.get(req.finding_id)

    async def event_stream() -> AsyncGenerator[str, None]:
        if cached:
            result_payload = json.dumps({
                "type": "result",
                "original_code": cached.get("original_code", ""),
                "fixed_code": cached.get("fixed_code", ""),
                "explanation": cached.get("explanation", ""),
            })
            yield f"data: {result_payload}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            return

        # Call Ollama for fix suggestion
        prompt = (
            f"You are a code improvement assistant. A code reviewer found this issue:\n\n"
            f"Issue: {req.description}\n"
            f"File: {req.file} (line {req.line})\n\n"
            f"Problematic code:\n```\n{req.code_snippet}\n```\n\n"
            f"Provide:\n"
            f"1. The ORIGINAL code (copy exactly as given)\n"
            f"2. The FIXED/IMPROVED version of this specific code snippet\n\n"
            f"Return JSON:\n"
            f'{{\n'
            f'  "original_code": "<exact original code>",\n'
            f'  "fixed_code": "<improved version>",\n'
            f'  "explanation": "<1-2 sentences explaining the fix>"\n'
            f'}}'
        )

        try:
            from utils.ollama import ollama_chat, parse_llm_json
            response = await ollama_chat(prompt, timeout=120)
            parsed = parse_llm_json(response, default=None)

            if parsed and isinstance(parsed, dict):
                result = {
                    "original_code": parsed.get("original_code", req.code_snippet),
                    "fixed_code": parsed.get("fixed_code", ""),
                    "explanation": parsed.get("explanation", ""),
                }
            else:
                result = {
                    "original_code": req.code_snippet,
                    "fixed_code": "",
                    "explanation": "Could not generate fix suggestion.",
                }

            # Cache result
            _fix_cache[req.finding_id] = result

            result_payload = json.dumps({
                "type": "result",
                "original_code": result["original_code"],
                "fixed_code": result["fixed_code"],
                "explanation": result["explanation"],
            })
            yield f"data: {result_payload}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Ollama not available'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
