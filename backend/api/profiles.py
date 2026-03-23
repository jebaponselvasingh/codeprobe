import json
import uuid
from typing import Any, Dict, List, Optional

import aiosqlite
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import DB_PATH

router = APIRouter()


class ProfileCreate(BaseModel):
    name: str
    description: str = ""
    agent_config: Dict[str, Any] = {}  # skip_agents, strictness
    scoring_weights: Dict[str, float] = {}  # category -> weight overrides
    llm_tone: str = "constructive and direct"


class RubricCategory(BaseModel):
    name: str
    weight: float  # 0-1, must sum to 1.0
    min_expectations: str = ""


class RubricCreate(BaseModel):
    name: str
    categories: List[RubricCategory]


@router.get("/profiles")
async def list_profiles():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, name, description, is_builtin, config_json FROM profiles ORDER BY is_builtin DESC, name"
        )
        rows = await cursor.fetchall()

    result = []
    for row in rows:
        config = json.loads(row["config_json"] or "{}")
        result.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "is_builtin": bool(row["is_builtin"]),
            "strictness": config.get("strictness", "moderate"),
            "skip_agents": config.get("skip_agents", []),
            "llm_tone": config.get("llm_tone", ""),
            "scoring_weights": config.get("scoring_weights", {}),
        })
    return result


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM profiles WHERE id=?", (profile_id,))
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, "Profile not found")
    config = json.loads(row["config_json"] or "{}")
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "is_builtin": bool(row["is_builtin"]),
        **config
    }


@router.post("/profiles")
async def create_profile(body: ProfileCreate):
    pid = str(uuid.uuid4())[:8]
    config = {
        "skip_agents": body.agent_config.get("skip_agents", []),
        "strictness": body.agent_config.get("strictness", "moderate"),
        "llm_tone": body.llm_tone,
        "scoring_weights": body.scoring_weights,
    }
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO profiles (id, name, description, is_builtin, config_json) VALUES (?,?,?,0,?)",
            (pid, body.name, body.description, json.dumps(config))
        )
        await db.commit()
    return {"id": pid}


@router.put("/profiles/{profile_id}")
async def update_profile(profile_id: str, body: ProfileCreate):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT is_builtin FROM profiles WHERE id=?", (profile_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Profile not found")
        if row["is_builtin"]:
            raise HTTPException(403, "Cannot modify built-in profiles")
        config = {
            "skip_agents": body.agent_config.get("skip_agents", []),
            "strictness": body.agent_config.get("strictness", "moderate"),
            "llm_tone": body.llm_tone,
            "scoring_weights": body.scoring_weights,
        }
        await db.execute(
            "UPDATE profiles SET name=?, description=?, config_json=? WHERE id=?",
            (body.name, body.description, json.dumps(config), profile_id)
        )
        await db.commit()
    return {"id": profile_id}


@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT is_builtin FROM profiles WHERE id=?", (profile_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Profile not found")
        if row["is_builtin"]:
            raise HTTPException(403, "Cannot delete built-in profiles")
        await db.execute("DELETE FROM profiles WHERE id=?", (profile_id,))
        await db.commit()
    return {"ok": True}


@router.get("/rubrics")
async def list_rubrics():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, name, categories_json, created_at FROM rubrics ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "categories": json.loads(r["categories_json"] or "[]"),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.post("/rubrics")
async def create_rubric(body: RubricCreate):
    rid = str(uuid.uuid4())[:8]
    cats = [c.model_dump() for c in body.categories]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO rubrics (id, name, categories_json) VALUES (?,?,?)",
            (rid, body.name, json.dumps(cats))
        )
        await db.commit()
    return {"id": rid}


@router.put("/rubrics/{rubric_id}")
async def update_rubric(rubric_id: str, body: RubricCreate):
    cats = [c.model_dump() for c in body.categories]
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id FROM rubrics WHERE id=?", (rubric_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "Rubric not found")
        await db.execute(
            "UPDATE rubrics SET name=?, categories_json=? WHERE id=?",
            (body.name, json.dumps(cats), rubric_id)
        )
        await db.commit()
    return {"id": rubric_id}


@router.delete("/rubrics/{rubric_id}")
async def delete_rubric(rubric_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM rubrics WHERE id=?", (rubric_id,))
        await db.commit()
    return {"ok": True}
