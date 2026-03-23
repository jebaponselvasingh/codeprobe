import asyncio
import re
from typing import Any, Dict, List, Optional
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json


class FastAPIAgent(AgentBase):
    agent_id = "fastapi"
    agent_name = "FastAPI Evaluator"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Running static analysis on FastAPI/Python backend files...")

        backend_files = state.get("backend_files", {})

        if not backend_files:
            self.emit(queue, "progress", "No backend files found, skipping FastAPI evaluation")
            return {
                **state,
                "fastapi_evaluation": {
                    "score": 5.0,
                    "sub_scores": {},
                    "findings": [],
                    "stats": {},
                    "llm_analysis": None,
                },
            }

        # --- Static analysis ---
        stats = self._static_analysis(backend_files)
        static_score = self._compute_static_score(stats)

        self.emit(queue, "progress",
                  f"Static analysis complete: {stats['endpoint_count']} endpoints, "
                  f"{stats['pydantic_model_count']} Pydantic models, "
                  f"{stats['try_except_count']} try/except blocks")

        # --- LLM analysis ---
        llm_context = self.get_llm_context(state)
        llm_result = await self._llm_analysis(backend_files, queue, llm_context)

        # Combine scores
        if llm_result and llm_result.get("score") is not None:
            llm_score = float(llm_result.get("score", static_score))
            final_score = round(0.4 * static_score + 0.6 * llm_score, 2)
            final_score = max(0.0, min(10.0, final_score))
            sub_scores = llm_result.get("sub_scores", {})
            findings = llm_result.get("findings", [])
        else:
            final_score = static_score
            sub_scores = {}
            findings = []

        self.emit(queue, "result", data={"score": final_score})

        return {
            **state,
            "fastapi_evaluation": {
                "score": final_score,
                "sub_scores": sub_scores,
                "findings": findings,
                "stats": stats,
                "llm_analysis": llm_result,
            },
        }

    def _static_analysis(self, backend_files: Dict[str, Any]) -> Dict[str, Any]:
        """Run pure regex-based static analysis over Python backend files."""
        endpoint_count = 0
        pydantic_model_count = 0
        depends_count = 0
        http_exception_count = 0
        try_except_count = 0
        async_def_count = 0
        sync_def_count = 0
        raw_sql_count = 0
        has_cors = False
        has_auth = False
        has_env_vars = False
        total_lines = 0

        for entry in backend_files.values():
            content = entry.get("content", "")

            # Endpoint decorators
            endpoint_count += len(re.findall(
                r"@(?:app|router)\.(get|post|put|patch|delete)\s*\(", content
            ))

            # Pydantic models
            pydantic_model_count += len(re.findall(
                r"class\s+\w+\s*\(\s*BaseModel\s*\)", content
            ))

            # Dependency injection
            depends_count += len(re.findall(r"\bDepends\s*\(", content))

            # HTTPException
            http_exception_count += len(re.findall(r"\bHTTPException\s*\(", content))

            # try/except blocks
            try_except_count += len(re.findall(r"\btry\s*:", content))

            # async vs sync handlers
            async_def_count += len(re.findall(r"\basync\s+def\s+\w+", content))
            sync_def_count += len(re.findall(r"(?<!\basync\s)\bdef\s+\w+", content))

            # Raw SQL with f-strings (potential injection risk)
            raw_sql_count += len(re.findall(r'\.execute\s*\(\s*f["\']', content))

            # CORS middleware
            if re.search(r"CORSMiddleware", content):
                has_cors = True

            # Auth patterns
            if re.search(r"verify_token|get_current_user|OAuth|JWT|Bearer", content):
                has_auth = True

            # Environment variables
            if re.search(r"os\.getenv|Settings\b", content):
                has_env_vars = True

            total_lines += content.count("\n") + 1

        return {
            "endpoint_count": endpoint_count,
            "pydantic_model_count": pydantic_model_count,
            "depends_count": depends_count,
            "http_exception_count": http_exception_count,
            "try_except_count": try_except_count,
            "async_def_count": async_def_count,
            "sync_def_count": sync_def_count,
            "raw_sql_count": raw_sql_count,
            "has_cors": has_cors,
            "has_auth": has_auth,
            "has_env_vars": has_env_vars,
            "total_lines": total_lines,
        }

    def _compute_static_score(self, stats: Dict[str, Any]) -> float:
        """Compute a 0-10 score from static analysis results."""
        score = 5.0

        # Reward good practices
        if stats["pydantic_model_count"] > 0:
            score += min(1.0, stats["pydantic_model_count"] * 0.2)

        if stats["depends_count"] > 0:
            score += 0.3

        if stats["has_cors"]:
            score += 0.2

        if stats["has_auth"]:
            score += 0.5

        if stats["has_env_vars"]:
            score += 0.3

        if stats["http_exception_count"] > 0:
            score += 0.2

        # Reward async usage
        total_defs = stats["async_def_count"] + stats["sync_def_count"]
        if total_defs > 0:
            async_ratio = stats["async_def_count"] / total_defs
            if async_ratio > 0.5:
                score += 0.3

        # Reward error handling
        if stats["try_except_count"] > 0:
            score += min(0.5, stats["try_except_count"] * 0.1)

        # Penalize raw SQL f-strings (SQL injection risk)
        if stats["raw_sql_count"] > 0:
            score -= min(2.0, stats["raw_sql_count"] * 0.5)

        # Penalize no endpoints at all
        if stats["endpoint_count"] == 0:
            score -= 1.0

        return round(max(0.0, min(10.0, score)), 2)

    async def _llm_analysis(self, backend_files: Dict[str, Any], queue: asyncio.Queue, llm_context: str = "") -> Optional[Dict]:
        """Run LLM analysis on top 8 backend files by size."""
        self.emit(queue, "progress", "Running LLM analysis on backend files...")

        # Pick top 8 files by size
        sorted_files = sorted(backend_files.items(), key=lambda x: x[1].get("size", 0), reverse=True)
        top_files = sorted_files[:8]

        # Build prompt, truncating to ~6000 chars total
        file_sections = []
        total_chars = 0
        max_chars = 6000

        for path, entry in top_files:
            content = entry.get("content", "")
            header = f"\n--- {path} ---\n"
            available = max_chars - total_chars - len(header) - 100
            if available <= 0:
                break
            snippet = content[:available]
            section = header + snippet
            file_sections.append(section)
            total_chars += len(section)
            if total_chars >= max_chars:
                break

        combined = "".join(file_sections)

        prompt = f"""{llm_context + chr(10) + chr(10) if llm_context else ""}Review these FastAPI Python files for API design quality, security issues, performance, and best practices.

{combined}

Return ONLY valid JSON with this exact structure:
{{
  "findings": [
    {{"type": "error|warning|suggestion", "area": "security|performance|validation|async_usage|other", "detail": "description", "file": "filename", "line": 0, "fix_hint": "how to fix"}}
  ],
  "sub_scores": {{
    "endpoints": 0.0,
    "security": 0.0,
    "validation": 0.0,
    "async_usage": 0.0
  }},
  "strengths": ["strength1", "strength2"],
  "score": 0.0
}}

Score range: 0-10. Focus on FastAPI-specific patterns and Python best practices."""

        try:
            response = await ollama_chat(prompt, timeout=180)
            if not response:
                return None

            parsed = parse_llm_json(response, default=None)
            if not parsed or not isinstance(parsed, dict):
                return None

            # Validate/fill structure
            if "score" not in parsed:
                parsed["score"] = 5.0
            if "findings" not in parsed:
                parsed["findings"] = []
            if "sub_scores" not in parsed:
                parsed["sub_scores"] = {}
            if "strengths" not in parsed:
                parsed["strengths"] = []

            return parsed

        except Exception as e:
            self.emit(queue, "progress", f"LLM analysis failed: {e}, using static score only")
            return None
