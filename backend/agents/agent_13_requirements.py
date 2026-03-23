import asyncio
import re
from typing import Any, Dict, List, Optional
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json


class RequirementsAgent(AgentBase):
    agent_id = "requirements"
    agent_name = "Requirements Validator"
    phase = 3

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        problem_statement = state.get("problem_statement")

        if not problem_statement or not problem_statement.strip():
            self.emit(queue, "progress", "No problem statement provided, skipping requirements validation")
            return {**state, "functional_validation": None}

        self.emit(queue, "progress", "Starting requirements validation pipeline...")

        frontend_files = state.get("frontend_files", {})
        backend_files = state.get("backend_files", {})
        all_files = {**frontend_files, **backend_files}

        # Combine all code for evidence search
        all_code = self._combine_code(all_files)

        # Pass 1: Parse requirements from problem statement
        self.emit(queue, "progress", "Pass 1/5: Parsing requirements from problem statement...")
        parsed_requirements, implicit_requirements = await self._pass1_parse_requirements(
            problem_statement, queue
        )

        # Pass 2: Static evidence search (no LLM)
        self.emit(queue, "progress", "Pass 2/5: Searching code for evidence of requirements...")
        evidence_map = self._pass2_evidence_search(parsed_requirements, all_files)

        # Pass 3: LLM validates each requirement against evidence
        self.emit(queue, "progress", "Pass 3/5: Validating requirements against evidence...")
        validation_results = await self._pass3_validate_requirements(
            parsed_requirements, evidence_map, all_code, queue
        )

        # Pass 4: LLM traces E2E flows
        self.emit(queue, "progress", "Pass 4/5: Tracing end-to-end flows...")
        flow_validations = await self._pass4_flow_tracing(
            problem_statement, parsed_requirements, all_code, queue
        )

        # Pass 5: LLM generates test scenarios
        self.emit(queue, "progress", "Pass 5/5: Generating test scenarios...")
        test_scenarios = await self._pass5_test_scenarios(
            problem_statement, parsed_requirements, validation_results, queue
        )

        # Aggregate results
        summary = self._build_summary(parsed_requirements, validation_results)
        gap_analysis = self._build_gap_analysis(validation_results, flow_validations)
        traceability_matrix = self._build_traceability_matrix(parsed_requirements, validation_results, evidence_map)

        functional_validation = {
            "parsed_requirements": parsed_requirements,
            "implicit_requirements": implicit_requirements,
            "validation_results": validation_results,
            "flow_validations": flow_validations,
            "test_scenarios": test_scenarios,
            "traceability_matrix": traceability_matrix,
            "summary": summary,
            "gap_analysis": gap_analysis,
        }

        score = summary.get("score", 5.0)
        self.emit(queue, "result", data={"score": score, "requirements_count": len(parsed_requirements)})
        self.emit(queue, "progress", f"Requirements validation complete: {summary.get('implemented_count', 0)}/{len(parsed_requirements)} requirements implemented")

        return {**state, "functional_validation": functional_validation}

    def _combine_code(self, all_files: Dict[str, Any]) -> str:
        """Combine all code into a single string for analysis, truncated."""
        sections = []
        total = 0
        max_total = 12000

        for path, entry in all_files.items():
            content = entry.get("content", "")
            header = f"\n=== {path} ===\n"
            available = max_total - total - len(header)
            if available <= 0:
                break
            snippet = content[:available]
            sections.append(header + snippet)
            total += len(header) + len(snippet)
            if total >= max_total:
                break

        return "".join(sections)

    async def _pass1_parse_requirements(
        self, problem_statement: str, queue: asyncio.Queue
    ) -> tuple[List[Dict], List[Dict]]:
        """Parse problem statement into explicit and implicit requirements."""
        prompt = f"""Parse the following project problem statement into structured requirements.

Problem Statement:
{problem_statement}

Return ONLY valid JSON:
{{
  "explicit_requirements": [
    {{"id": "REQ-001", "category": "functional|authentication|data|ui|api|other", "description": "requirement text", "priority": "must|should|nice-to-have", "acceptance_criteria": ["criterion1"]}}
  ],
  "implicit_requirements": [
    {{"id": "IMP-001", "description": "implied requirement (e.g., error handling, loading states)", "category": "ux|security|performance|reliability"}}
  ]
}}

Extract ALL explicit requirements stated and infer reasonable implicit requirements."""

        try:
            response = await ollama_chat(prompt, timeout=120)
            parsed = parse_llm_json(response, default=None)

            if parsed and isinstance(parsed, dict):
                explicit = parsed.get("explicit_requirements", [])
                implicit = parsed.get("implicit_requirements", [])
                return explicit, implicit
        except Exception as e:
            self.emit(queue, "progress", f"Pass 1 failed: {e}")

        # Fallback: basic parsing from problem statement lines
        lines = [l.strip() for l in problem_statement.splitlines() if l.strip() and len(l.strip()) > 10]
        fallback_reqs = [
            {"id": f"REQ-{i+1:03d}", "category": "functional", "description": line, "priority": "must", "acceptance_criteria": []}
            for i, line in enumerate(lines[:20])
        ]
        return fallback_reqs, []

    def _pass2_evidence_search(
        self, requirements: List[Dict], all_files: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        """Search code for evidence of each requirement (no LLM)."""
        evidence_map: Dict[str, List[Dict]] = {}

        for req in requirements:
            req_id = req.get("id", "")
            description = req.get("description", "").lower()
            evidence_list = []

            # Extract keywords from the requirement description
            # Remove stop words
            stop_words = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "is", "are", "be", "that", "this", "it", "with"}
            words = re.findall(r"\b[a-z]{3,}\b", description)
            keywords = [w for w in words if w not in stop_words][:8]

            for path, entry in all_files.items():
                content_lower = entry.get("content", "").lower()
                matches = []
                for kw in keywords:
                    if kw in content_lower:
                        # Find line numbers
                        lines = entry.get("content", "").splitlines()
                        for i, line in enumerate(lines[:200], start=1):
                            if kw.lower() in line.lower():
                                matches.append({"keyword": kw, "line": i, "snippet": line.strip()[:100]})
                                break  # One match per keyword per file

                if matches:
                    evidence_list.append({
                        "file": path,
                        "matches": matches[:5],
                        "keyword_hit_count": len(matches),
                    })

            evidence_map[req_id] = evidence_list

        return evidence_map

    async def _pass3_validate_requirements(
        self,
        requirements: List[Dict],
        evidence_map: Dict[str, List[Dict]],
        all_code: str,
        queue: asyncio.Queue,
    ) -> List[Dict]:
        """LLM validates each requirement against collected evidence."""
        if not requirements:
            return []

        # Build a compact evidence summary
        evidence_summary = []
        for req in requirements:
            req_id = req.get("id", "")
            evidence = evidence_map.get(req_id, [])
            files_with_evidence = [e["file"] for e in evidence]
            evidence_summary.append({
                "id": req_id,
                "description": req.get("description", ""),
                "evidence_files": files_with_evidence,
                "evidence_count": sum(e["keyword_hit_count"] for e in evidence),
            })

        prompt = f"""Given these project requirements and code evidence, validate each requirement.

Requirements with evidence:
{_json_compact(evidence_summary[:15])}

Code sample (first 4000 chars):
{all_code[:4000]}

For each requirement, determine if it's implemented. Return ONLY valid JSON:
{{
  "validations": [
    {{
      "id": "REQ-001",
      "status": "implemented|partial|missing",
      "confidence": 0.0,
      "evidence_notes": "what was found",
      "gaps": ["what's missing"]
    }}
  ]
}}"""

        try:
            response = await ollama_chat(prompt, timeout=150)
            parsed = parse_llm_json(response, default=None)

            if parsed and isinstance(parsed, dict):
                validations = parsed.get("validations", [])
                # Index by id for easy lookup
                validation_by_id = {v["id"]: v for v in validations}

                results = []
                for req in requirements:
                    req_id = req.get("id", "")
                    val = validation_by_id.get(req_id, {})
                    results.append({
                        "id": req_id,
                        "description": req.get("description", ""),
                        "priority": req.get("priority", "must"),
                        "status": val.get("status", "missing"),
                        "confidence": val.get("confidence", 0.5),
                        "evidence_notes": val.get("evidence_notes", ""),
                        "gaps": val.get("gaps", []),
                        "evidence_files": [e["file"] for e in evidence_map.get(req_id, [])],
                    })
                return results

        except Exception as e:
            self.emit(queue, "progress", f"Pass 3 failed: {e}")

        # Fallback: use evidence map to determine status
        results = []
        for req in requirements:
            req_id = req.get("id", "")
            evidence = evidence_map.get(req_id, [])
            status = "implemented" if len(evidence) >= 2 else ("partial" if len(evidence) == 1 else "missing")
            results.append({
                "id": req_id,
                "description": req.get("description", ""),
                "priority": req.get("priority", "must"),
                "status": status,
                "confidence": 0.4,
                "evidence_notes": f"Found in {len(evidence)} file(s)" if evidence else "No direct evidence found",
                "gaps": [],
                "evidence_files": [e["file"] for e in evidence],
            })
        return results

    async def _pass4_flow_tracing(
        self,
        problem_statement: str,
        requirements: List[Dict],
        all_code: str,
        queue: asyncio.Queue,
    ) -> List[Dict]:
        """LLM traces end-to-end user flows."""
        if not requirements:
            return []

        req_descriptions = [
            f"{r.get('id','')}: {r.get('description','')}"
            for r in requirements[:10]
        ]

        prompt = f"""Trace end-to-end user flows for this application.

Problem Statement:
{problem_statement[:1000]}

Key Requirements:
{chr(10).join(req_descriptions)}

Code sample:
{all_code[:3000]}

Identify 3-5 main user flows and trace them through the code. Return ONLY valid JSON:
{{
  "flows": [
    {{
      "name": "User Authentication Flow",
      "steps": [
        {{"step": 1, "description": "User submits login form", "frontend_component": "LoginForm", "backend_endpoint": "POST /auth/login", "implemented": true}}
      ],
      "complete": true,
      "missing_steps": ["step description if any missing"]
    }}
  ]
}}"""

        try:
            response = await ollama_chat(prompt, timeout=150)
            parsed = parse_llm_json(response, default=None)

            if parsed and isinstance(parsed, dict):
                return parsed.get("flows", [])

        except Exception as e:
            self.emit(queue, "progress", f"Pass 4 failed: {e}")

        return []

    async def _pass5_test_scenarios(
        self,
        problem_statement: str,
        requirements: List[Dict],
        validation_results: List[Dict],
        queue: asyncio.Queue,
    ) -> List[Dict]:
        """LLM generates test scenarios based on requirements."""
        if not requirements:
            return []

        # Focus on missing/partial requirements
        gaps = [
            r for r in validation_results
            if r.get("status") in ("missing", "partial")
        ][:10]

        req_list = [
            f"{r.get('id','')}: {r.get('description','')}"
            for r in requirements[:10]
        ]

        prompt = f"""Generate test scenarios for this application.

Requirements:
{chr(10).join(req_list)}

Missing/Partial requirements:
{chr(10).join(f"- {g.get('id','')}: {g.get('description','')}" for g in gaps) or "(none)"}

Return ONLY valid JSON:
{{
  "test_scenarios": [
    {{
      "id": "TC-001",
      "requirement_id": "REQ-001",
      "title": "Test scenario title",
      "type": "unit|integration|e2e",
      "steps": ["step 1", "step 2"],
      "expected_result": "what should happen",
      "priority": "critical|high|medium|low"
    }}
  ]
}}

Generate 5-10 test scenarios covering the most important requirements."""

        try:
            response = await ollama_chat(prompt, timeout=120)
            parsed = parse_llm_json(response, default=None)

            if parsed and isinstance(parsed, dict):
                return parsed.get("test_scenarios", [])

        except Exception as e:
            self.emit(queue, "progress", f"Pass 5 failed: {e}")

        return []

    def _build_summary(
        self, requirements: List[Dict], validation_results: List[Dict]
    ) -> Dict:
        """Build a summary of the validation results."""
        total = len(requirements)
        implemented = sum(1 for r in validation_results if r.get("status") == "implemented")
        partial = sum(1 for r in validation_results if r.get("status") == "partial")
        missing = sum(1 for r in validation_results if r.get("status") == "missing")

        # Score: fully implemented counts 1.0, partial 0.5, missing 0
        if total > 0:
            raw_score = (implemented + partial * 0.5) / total
            score = round(raw_score * 10, 2)
        else:
            score = 5.0

        return {
            "total_requirements": total,
            "implemented_count": implemented,
            "partial_count": partial,
            "missing_count": missing,
            "completion_rate": round((implemented + partial * 0.5) / total, 2) if total > 0 else 0.0,
            "score": score,
        }

    def _build_gap_analysis(
        self, validation_results: List[Dict], flow_validations: List[Dict]
    ) -> Dict:
        """Build gap analysis from validation results."""
        critical_gaps = [
            r for r in validation_results
            if r.get("status") == "missing" and r.get("priority") == "must"
        ]
        partial_gaps = [
            r for r in validation_results
            if r.get("status") == "partial"
        ]
        incomplete_flows = [
            f for f in flow_validations
            if not f.get("complete", True)
        ]

        return {
            "critical_gaps": [
                {"id": g["id"], "description": g["description"], "gaps": g.get("gaps", [])}
                for g in critical_gaps
            ],
            "partial_implementations": [
                {"id": g["id"], "description": g["description"], "gaps": g.get("gaps", [])}
                for g in partial_gaps
            ],
            "incomplete_flows": [
                {"name": f.get("name"), "missing_steps": f.get("missing_steps", [])}
                for f in incomplete_flows
            ],
            "total_critical_gaps": len(critical_gaps),
            "total_partial": len(partial_gaps),
        }

    def _build_traceability_matrix(
        self,
        requirements: List[Dict],
        validation_results: List[Dict],
        evidence_map: Dict[str, List[Dict]],
    ) -> List[Dict]:
        """Build a traceability matrix linking requirements to code files."""
        validation_by_id = {v["id"]: v for v in validation_results}
        matrix = []

        for req in requirements:
            req_id = req.get("id", "")
            val = validation_by_id.get(req_id, {})
            evidence = evidence_map.get(req_id, [])

            matrix.append({
                "requirement_id": req_id,
                "description": req.get("description", "")[:100],
                "status": val.get("status", "missing"),
                "files": [e["file"] for e in evidence],
                "file_count": len(evidence),
            })

        return matrix


def _json_compact(obj) -> str:
    """Compact JSON serialization for prompts."""
    import json
    return json.dumps(obj, separators=(",", ":"), default=str)
