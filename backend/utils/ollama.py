import os
import httpx
import json
import logging

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")


async def ollama_chat(prompt: str, system: str = "", timeout: int = 180) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]
    except Exception as e:
        logger.warning(f"Ollama unavailable: {e}")
        return ""


async def ollama_available() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"ok": True, "models": models, "active_model": OLLAMA_MODEL}
    except Exception as e:
        return {"ok": False, "models": [], "active_model": OLLAMA_MODEL, "error": str(e)}


def parse_llm_json(text: str, default=None):
    """Extract and parse JSON from LLM response text."""
    if not text:
        return default
    import re
    # Try ```json ... ``` blocks first
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
    else:
        # Find first { or [
        start = min(
            (text.find("{") if "{" in text else len(text)),
            (text.find("[") if "[" in text else len(text)),
        )
        text = text[start:]
    try:
        return json.loads(text)
    except Exception:
        logger.warning(f"JSON parse failed on LLM response: {text[:200]}")
        return default
