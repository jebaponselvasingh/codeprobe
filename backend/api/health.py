from fastapi import APIRouter
from utils.ollama import ollama_available

router = APIRouter()


@router.get("/health")
async def health():
    ollama = await ollama_available()
    return {
        "status": "ok",
        "ollama": ollama["ok"],
        "models": ollama["models"],
        "active_model": ollama["active_model"],
        "db_status": "ok",
    }
