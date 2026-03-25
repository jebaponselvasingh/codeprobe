import asyncio
import json
import logging
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)


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

    def validate_output(
        self,
        raw: dict,
        schema_class: Type[BaseModel],
        queue: asyncio.Queue,
    ) -> dict:
        """
        Validate a parsed LLM response dict against a Pydantic schema.

        - On success: returns the schema's model_dump() (normalised, typed).
        - On failure: emits a non-fatal warning event and returns whichever
          recognised fields are present, leaving unrecognised keys out.
          Never raises — guardrails warn, they do not crash sessions.
        """
        try:
            return schema_class(**(raw or {})).model_dump()
        except Exception as exc:
            msg = f"[guardrail] {self.agent_id} output schema warning: {exc}"
            logger.warning(msg)
            self.emit(queue, "progress", msg)
            # Return only fields the schema knows about, with raw values
            known_fields = schema_class.model_fields.keys()
            return {k: v for k, v in (raw or {}).items() if k in known_fields}

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        raise NotImplementedError
