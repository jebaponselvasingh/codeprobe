import json
from fastapi import APIRouter, HTTPException
import aiosqlite
from database import DB_PATH
from utils.ollama import ollama_chat

router = APIRouter()

DIAGRAM_PROMPTS = {
    "component_tree": "Based on this React frontend code review, generate a Mermaid.js component tree diagram showing the main React components and their parent-child relationships. Use 'graph TD' syntax. Only output the Mermaid code, no explanation.",
    "api_flow": "Based on this full-stack code review, generate a Mermaid.js sequence diagram showing the API flow between frontend and backend. Show key API calls and data flow. Use 'sequenceDiagram' syntax. Only output the Mermaid code, no explanation.",
    "data_model": "Based on this code review, generate a Mermaid.js entity relationship diagram showing the main data models and their relationships. Use 'erDiagram' syntax. Only output the Mermaid code, no explanation.",
    "dependency_graph": "Based on this code review, generate a Mermaid.js graph showing the module/package dependencies. Use 'graph LR' syntax. Only output the Mermaid code, no explanation.",
}


@router.get("/review/{session_id}/diagram/{diagram_type}")
async def get_diagram(session_id: str, diagram_type: str):
    if diagram_type not in DIAGRAM_PROMPTS:
        raise HTTPException(400, f"Unknown diagram type. Valid: {list(DIAGRAM_PROMPTS.keys())}")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT report_json FROM reviews WHERE session_id=?", (session_id,))
        row = await cursor.fetchone()

    if not row or not row["report_json"]:
        raise HTTPException(404, "Review not found or not complete")

    report = json.loads(row["report_json"])

    # Build context from report
    structure = report.get("agents", {}).get("structure_analysis", {})
    react_eval = report.get("agents", {}).get("react_evaluation", {})
    integration = report.get("agents", {}).get("integration_analysis", {})

    context = f"""Code Review Report Summary:
- Overall Score: {report.get('scores', {}).get('overall', 0)}/10
- Structure: {json.dumps(structure, indent=2)[:1500]}
- Frontend Analysis: {json.dumps(react_eval, indent=2)[:1000]}
- Integration Analysis: {json.dumps(integration, indent=2)[:1000]}
"""

    prompt = f"{DIAGRAM_PROMPTS[diagram_type]}\n\nContext:\n{context}"

    mermaid_code = await ollama_chat(
        prompt=prompt,
        system="You are a software architecture diagram generator. Generate valid Mermaid.js code only. No markdown fences, no explanation text.",
        timeout=60,
    )

    # Clean up: remove markdown fences if present
    mermaid_code = mermaid_code.strip()
    for fence in ["```mermaid", "```"]:
        mermaid_code = mermaid_code.replace(fence, "")
    mermaid_code = mermaid_code.strip()

    # Fallback if Ollama unavailable
    if not mermaid_code:
        fallbacks = {
            "component_tree": "graph TD\n  App --> Header\n  App --> Main\n  App --> Footer\n  Main --> Content",
            "api_flow": "sequenceDiagram\n  Frontend->>Backend: POST /review\n  Backend->>Frontend: SSE Stream\n  Frontend->>Backend: GET /report",
            "data_model": "erDiagram\n  REVIEW ||--o{ FINDING : has\n  REVIEW ||--o{ CHAT_MESSAGE : has",
            "dependency_graph": "graph LR\n  React --> Router\n  React --> Zustand\n  FastAPI --> SQLite\n  FastAPI --> Ollama",
        }
        mermaid_code = fallbacks.get(diagram_type, "graph TD\n  A --> B")

    return {"mermaid_code": mermaid_code, "diagram_type": diagram_type}
