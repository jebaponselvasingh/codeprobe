import json
from typing import Optional

import aiosqlite
from fastapi import APIRouter, HTTPException

from database import DB_PATH

router = APIRouter()


@router.get("/history/{project_id}/progress")
async def get_progress(project_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT version, overall_score, grade, category_scores_json, report_json, created_at
               FROM reviews WHERE project_id=? ORDER BY version ASC""",
            (project_id,)
        )
        rows = [dict(r) for r in await cursor.fetchall()]

    if not rows:
        raise HTTPException(404, "No reviews found for this project")

    versions = []
    for row in rows:
        cat_scores = json.loads(row["category_scores_json"] or "{}")
        versions.append({
            "version": row["version"],
            "grade": row["grade"],
            "overall_score": row["overall_score"],
            "scores_by_category": {k: v["score"] if isinstance(v, dict) else v for k, v in cat_scores.items()},
            "date": row["created_at"],
        })

    trends = {"improving": [], "declining": [], "stable": []}
    if len(versions) >= 2:
        first = versions[0]["scores_by_category"]
        last = versions[-1]["scores_by_category"]
        for cat in first:
            if cat in last:
                delta = last[cat] - first[cat]
                if delta > 0.5:
                    trends["improving"].append(cat)
                elif delta < -0.5:
                    trends["declining"].append(cat)
                else:
                    trends["stable"].append(cat)

    resolved_issues = []
    persistent_issues = []
    new_issues = []

    if len(rows) >= 2:
        prev_report = json.loads(rows[-2]["report_json"] or "{}")
        curr_report = json.loads(rows[-1]["report_json"] or "{}")
        prev_msgs = {f.get("message", "") for f in (prev_report.get("findings") or {}).get("critical", [])}
        curr_msgs = {f.get("message", "") for f in (curr_report.get("findings") or {}).get("critical", [])}
        resolved_issues = list(prev_msgs - curr_msgs)[:10]
        persistent_issues = list(prev_msgs & curr_msgs)[:10]
        new_issues = list(curr_msgs - prev_msgs)[:10]

    return {
        "project_id": project_id,
        "versions": versions,
        "trends": trends,
        "resolved_issues": resolved_issues,
        "persistent_issues": persistent_issues,
        "new_issues": new_issues,
    }


@router.get("/history/students/{student_name}")
async def get_student_history(student_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT session_id as review_id, project_id, version, overall_score, grade, created_at
               FROM reviews WHERE student_name=? ORDER BY created_at DESC LIMIT 50""",
            (student_name,)
        )
        items = [dict(r) for r in await cursor.fetchall()]
    return {"student_name": student_name, "reviews": items}
