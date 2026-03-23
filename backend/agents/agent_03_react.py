import asyncio
import re
from typing import Any, Dict, List
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json


class ReactAgent(AgentBase):
    agent_id = "react"
    agent_name = "React Evaluator"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Running static analysis on React/frontend files...")

        frontend_files = state.get("frontend_files", {})

        if not frontend_files:
            self.emit(queue, "progress", "No frontend files found, skipping React evaluation")
            return {
                **state,
                "react_evaluation": {
                    "score": 5.0,
                    "sub_scores": {},
                    "findings": [],
                    "stats": {},
                    "llm_analysis": None,
                },
            }

        # --- Static analysis ---
        stats = self._static_analysis(frontend_files)
        static_score = self._compute_static_score(stats)

        self.emit(queue, "progress",
                  f"Static analysis complete: {stats['use_state_count']} useState, "
                  f"{stats['use_effect_count']} useEffect, "
                  f"{stats['console_log_count']} console.logs")

        # --- LLM analysis ---
        llm_context = self.get_llm_context(state)
        llm_result = await self._llm_analysis(frontend_files, queue, llm_context)

        # Combine scores: if LLM succeeded, blend; otherwise use static only
        if llm_result and llm_result.get("score") is not None:
            llm_score = float(llm_result.get("score", static_score))
            # Blend: 40% static, 60% LLM
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
            "react_evaluation": {
                "score": final_score,
                "sub_scores": sub_scores,
                "findings": findings,
                "stats": stats,
                "llm_analysis": llm_result,
            },
        }

    def _static_analysis(self, frontend_files: Dict[str, Any]) -> Dict[str, Any]:
        """Run pure regex-based static analysis over frontend files."""
        use_state_count = 0
        use_effect_count = 0
        use_callback_count = 0
        use_memo_count = 0
        use_ref_count = 0
        custom_hook_count = 0
        has_error_boundary = False
        has_memoization = False
        has_lazy_loading = False
        console_log_count = 0
        any_type_count = 0
        inline_styles_count = 0
        map_calls = 0
        key_props = 0

        for entry in frontend_files.values():
            content = entry.get("content", "")

            use_state_count += len(re.findall(r"\buseState\s*\(", content))
            use_effect_count += len(re.findall(r"\buseEffect\s*\(", content))
            use_callback_count += len(re.findall(r"\buseCallback\s*\(", content))
            use_memo_count += len(re.findall(r"\buseMemo\s*\(", content))
            use_ref_count += len(re.findall(r"\buseRef\s*\(", content))

            # Custom hooks: functions starting with use + capital letter
            custom_hook_count += len(re.findall(r"\buse[A-Z]\w+\s*\(", content))

            if re.search(r"componentDidCatch|ErrorBoundary", content):
                has_error_boundary = True

            if re.search(r"React\.memo|(?<!\w)memo\s*\(", content):
                has_memoization = True

            if re.search(r"React\.lazy|(?<!\w)lazy\s*\(", content):
                has_lazy_loading = True

            console_log_count += len(re.findall(r"\bconsole\.log\s*\(", content))
            any_type_count += len(re.findall(r":\s*any\b", content))
            inline_styles_count += len(re.findall(r"style\s*=\s*\{\{", content))

            map_calls += len(re.findall(r"\.map\s*\(", content))
            key_props += len(re.findall(r"\bkey\s*=", content))

        # Estimate missing key props (rough heuristic)
        missing_keys = max(0, map_calls - key_props)

        return {
            "use_state_count": use_state_count,
            "use_effect_count": use_effect_count,
            "use_callback_count": use_callback_count,
            "use_memo_count": use_memo_count,
            "use_ref_count": use_ref_count,
            "custom_hook_count": custom_hook_count,
            "has_error_boundary": has_error_boundary,
            "has_memoization": has_memoization,
            "has_lazy_loading": has_lazy_loading,
            "console_log_count": console_log_count,
            "any_type_count": any_type_count,
            "inline_styles_count": inline_styles_count,
            "map_calls": map_calls,
            "key_props": key_props,
            "missing_keys_estimate": missing_keys,
        }

    def _compute_static_score(self, stats: Dict[str, Any]) -> float:
        """Compute a 0-10 score from static analysis results."""
        score = 5.0

        if stats["has_error_boundary"]:
            score += 0.5
        if stats["has_memoization"]:
            score += 0.3
        if stats["has_lazy_loading"]:
            score += 0.2

        # Penalize console.logs
        console_penalty = min(1.5, (stats["console_log_count"] // 3) * 0.1)
        score -= console_penalty

        # Penalize `any` type usage
        any_penalty = min(1.0, (stats["any_type_count"] // 5) * 0.1)
        score -= any_penalty

        # Penalize missing keys
        if stats["missing_keys_estimate"] > 3:
            score -= 0.3

        # Penalize excessive inline styles
        if stats["inline_styles_count"] > 10:
            score -= 0.2

        return round(max(0.0, min(10.0, score)), 2)

    async def _llm_analysis(self, frontend_files: Dict[str, Any], queue: asyncio.Queue, llm_context: str = "") -> Dict | None:
        """Run LLM analysis on top 8 frontend files by size."""
        self.emit(queue, "progress", "Running LLM analysis on frontend files...")

        # Pick top 8 files by size
        sorted_files = sorted(frontend_files.items(), key=lambda x: x[1].get("size", 0), reverse=True)
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

        prompt = f"""{llm_context + chr(10) + chr(10) if llm_context else ""}Review these React/TypeScript frontend files for code quality, best practices, performance, and maintainability.

{combined}

Return ONLY valid JSON with this exact structure:
{{
  "findings": [
    {{"type": "error|warning|suggestion", "area": "hooks|components|types|performance|accessibility|other", "detail": "description", "file": "filename", "line": 0, "fix_hint": "how to fix"}}
  ],
  "sub_scores": {{
    "component_design": 0.0,
    "hooks_usage": 0.0,
    "typescript_quality": 0.0,
    "performance": 0.0
  }},
  "strengths": ["strength1", "strength2"],
  "score": 0.0
}}

Score range: 0-10. Be specific and actionable."""

        try:
            response = await ollama_chat(prompt, timeout=180)
            if not response:
                return None

            parsed = parse_llm_json(response, default=None)
            if not parsed or not isinstance(parsed, dict):
                return None

            # Validate structure
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
