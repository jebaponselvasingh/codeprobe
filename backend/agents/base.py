import asyncio
import json
from typing import Any, Dict, Optional


class AgentBase:
    agent_id: str = "base"
    agent_name: str = "Base Agent"
    phase: int = 1

    def emit(self, queue: asyncio.Queue, event_type: str, message: str = "", data: Any = None, fatal: bool = False):
        event = {
            "type": event_type,
            "agent": self.agent_id,
            "phase": self.phase,
            "message": message,
        }
        if data is not None:
            event["data"] = data
        if fatal:
            event["fatal"] = True
        queue.put_nowait(event)

    def get_llm_context(self, state: Dict[str, Any]) -> str:
        """Return a prompt prefix with profile strictness, tone, and rubric expectations."""
        profile = state.get("profile_config") or {}
        strictness = profile.get("strictness", "moderate")
        tone = profile.get("llm_tone", "constructive and direct")
        lines = [
            f"Review strictness: {strictness}.",
            f"Tone: {tone}.",
        ]
        rubric = state.get("rubric_config") or {}
        cats = rubric.get("categories", [])
        if cats:
            expectations = [
                f"{c['name']}: {c['min_expectations']}"
                for c in cats
                if c.get("min_expectations")
            ]
            if expectations:
                lines.append("Rubric requirements: " + "; ".join(expectations))
        return "\n".join(lines)

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        raise NotImplementedError
