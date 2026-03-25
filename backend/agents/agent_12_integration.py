import asyncio
import re
from typing import Any, Dict, List, Optional, Set
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json
from guardrails.schemas import IntegrationLLMOutput, clamp_score


class IntegrationAgent(AgentBase):
    agent_id = "integration"
    agent_name = "Integration Analyzer"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Analyzing frontend-backend integration...")

        backend_files = state.get("backend_files", {})
        frontend_files = state.get("frontend_files", {})

        # --- Extract backend endpoints ---
        be_endpoints = self._extract_be_endpoints(backend_files)
        self.emit(queue, "progress", f"Found {len(be_endpoints)} backend endpoints")

        # --- Extract frontend API calls ---
        fe_calls = self._extract_fe_calls(frontend_files)
        self.emit(queue, "progress", f"Found {len(fe_calls)} frontend API calls")

        # --- Match endpoints ---
        endpoint_map, unmatched_fe, unused_be = self._match_endpoints(be_endpoints, fe_calls)

        match_rate = 0.0
        if be_endpoints:
            match_rate = len([e for e in be_endpoints if e not in unused_be]) / len(be_endpoints)

        static_score = self._compute_score(be_endpoints, fe_calls, unmatched_fe, unused_be)

        # --- LLM contract analysis ---
        llm_result = await self._llm_analysis(
            be_endpoints, fe_calls, unmatched_fe, unused_be, queue
        )

        if llm_result and llm_result.get("score") is not None:
            llm_score = float(llm_result.get("score", static_score))
            final_score = round(0.5 * static_score + 0.5 * llm_score, 2)
            final_score = max(0.0, min(10.0, final_score))
        else:
            final_score = static_score
            llm_result = {}

        self.emit(queue, "result", data={
            "score": final_score,
            "be_endpoint_count": len(be_endpoints),
            "fe_call_count": len(fe_calls),
            "match_rate": round(match_rate, 2),
        })

        return {
            **state,
            "integration_analysis": {
                "score": final_score,
                "endpoint_map": endpoint_map,
                "be_endpoints": be_endpoints,
                "fe_calls": fe_calls,
                "unmatched_fe": unmatched_fe,
                "unused_be": unused_be,
                "match_rate": round(match_rate, 2),
                "llm_analysis": llm_result,
            },
        }

    def _normalize_path(self, path: str) -> str:
        """Normalize an endpoint path for comparison."""
        path = path.lower().strip()
        # Strip trailing slash
        path = path.rstrip("/")
        # Normalize path parameters: {param} and :param -> {param}
        path = re.sub(r":(\w+)", r"{\1}", path)
        # Strip /api prefix for comparison
        path = re.sub(r"^/api", "", path)
        if not path:
            path = "/"
        return path

    def _extract_be_endpoints(self, backend_files: Dict[str, Any]) -> List[str]:
        """Extract endpoint paths from FastAPI route decorators."""
        endpoints = []
        pattern = re.compile(
            r"@(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]"
        )
        for path, entry in backend_files.items():
            content = entry.get("content", "")
            for match in pattern.finditer(content):
                method = match.group(1).upper()
                route = match.group(2)
                endpoints.append(f"{method} {route}")
        return list(set(endpoints))

    def _extract_fe_calls(self, frontend_files: Dict[str, Any]) -> List[str]:
        """Extract API call URLs from frontend files."""
        calls = []
        # fetch() calls
        fetch_pattern = re.compile(
            r"fetch\s*\(\s*[`'\"]([^`'\"]+)[`'\"]"
        )
        # axios method calls
        axios_pattern = re.compile(
            r"axios\.(get|post|put|delete|patch)\s*\(\s*[`'\"]([^`'\"]+)[`'\"]"
        )
        # Template literals with backticks for URL variables
        template_pattern = re.compile(
            r"(?:fetch|axios\.(?:get|post|put|delete|patch))\s*\(\s*`([^`]+)`"
        )

        for path, entry in frontend_files.items():
            content = entry.get("content", "")

            for match in fetch_pattern.finditer(content):
                url = match.group(1)
                if "/" in url:
                    calls.append(url)

            for match in axios_pattern.finditer(content):
                url = match.group(2)
                if "/" in url:
                    calls.append(url)

            for match in template_pattern.finditer(content):
                url = match.group(1)
                # Simplify template literal: replace ${...} with {param}
                url = re.sub(r"\$\{[^}]+\}", "{param}", url)
                if "/" in url:
                    calls.append(url)

        return list(set(calls))

    def _match_endpoints(
        self,
        be_endpoints: List[str],
        fe_calls: List[str],
    ) -> tuple[List[Dict], List[str], List[str]]:
        """Match frontend calls to backend endpoints."""
        # Normalize BE endpoints
        be_normalized = {}
        for ep in be_endpoints:
            parts = ep.split(" ", 1)
            if len(parts) == 2:
                method, path = parts
                norm = self._normalize_path(path)
                be_normalized[norm] = ep

        # Normalize FE calls
        fe_normalized = {}
        for call in fe_calls:
            norm = self._normalize_path(call)
            fe_normalized[norm] = call

        # Match
        endpoint_map = []
        matched_be = set()

        for fe_norm, fe_original in fe_normalized.items():
            matched = False
            for be_norm, be_original in be_normalized.items():
                if fe_norm == be_norm or self._paths_match(fe_norm, be_norm):
                    endpoint_map.append({
                        "fe_call": fe_original,
                        "be_endpoint": be_original,
                        "matched": True,
                    })
                    matched_be.add(be_norm)
                    matched = True
                    break
            if not matched:
                endpoint_map.append({
                    "fe_call": fe_original,
                    "be_endpoint": None,
                    "matched": False,
                })

        unmatched_fe = [
            item["fe_call"] for item in endpoint_map if not item["matched"]
        ]
        unused_be = [
            ep for norm, ep in be_normalized.items() if norm not in matched_be
        ]

        return endpoint_map, unmatched_fe, unused_be

    def _paths_match(self, path1: str, path2: str) -> bool:
        """Check if two normalized paths match, accounting for path parameters."""
        parts1 = path1.split("/")
        parts2 = path2.split("/")
        if len(parts1) != len(parts2):
            return False
        for p1, p2 in zip(parts1, parts2):
            if p1 == p2:
                continue
            if p1.startswith("{") or p2.startswith("{"):
                continue
            return False
        return True

    def _compute_score(
        self,
        be_endpoints: List[str],
        fe_calls: List[str],
        unmatched_fe: List[str],
        unused_be: List[str],
    ) -> float:
        """Compute integration score."""
        if not be_endpoints and not fe_calls:
            return 5.0

        score = 7.0

        # Penalize unmatched FE calls
        if fe_calls:
            unmatched_ratio = len(unmatched_fe) / len(fe_calls)
            score -= unmatched_ratio * 2.0

        # Penalize unused BE endpoints
        if be_endpoints:
            unused_ratio = len(unused_be) / len(be_endpoints)
            score -= unused_ratio * 1.0

        # Bonus for having both FE and BE with good coverage
        if be_endpoints and fe_calls and len(unmatched_fe) == 0:
            score += 1.0

        return round(max(0.0, min(10.0, score)), 2)

    async def _llm_analysis(
        self,
        be_endpoints: List[str],
        fe_calls: List[str],
        unmatched_fe: List[str],
        unused_be: List[str],
        queue: asyncio.Queue,
    ) -> Optional[Dict]:
        """Run LLM analysis on endpoint mapping."""
        self.emit(queue, "progress", "Running LLM contract analysis...")

        if not be_endpoints and not fe_calls:
            return None

        be_list = "\n".join(be_endpoints[:30]) or "(none)"
        fe_list = "\n".join(fe_calls[:30]) or "(none)"
        unmatched_list = "\n".join(unmatched_fe[:15]) or "(none)"
        unused_list = "\n".join(unused_be[:15]) or "(none)"

        prompt = f"""Analyze the API contract between frontend and backend.

Backend endpoints:
{be_list}

Frontend API calls:
{fe_list}

Unmatched frontend calls (no backend endpoint):
{unmatched_list}

Unused backend endpoints (not called by frontend):
{unused_list}

Return ONLY valid JSON:
{{
  "findings": [
    {{"type": "error|warning|suggestion", "detail": "description", "fix_hint": "how to fix"}}
  ],
  "strengths": ["strength1"],
  "contract_issues": ["issue1", "issue2"],
  "score": 0.0
}}

Score 0-10 based on integration completeness and API contract quality."""

        try:
            response = await ollama_chat(prompt, timeout=120)
            if not response:
                return None

            parsed = parse_llm_json(response, default=None)
            if not parsed or not isinstance(parsed, dict):
                return None

            validated = self.validate_output(parsed, IntegrationLLMOutput, queue)
            validated["score"] = clamp_score(validated.get("score", 5.0))
            return validated

        except Exception as e:
            self.emit(queue, "progress", f"LLM integration analysis failed: {e}")
            return None
