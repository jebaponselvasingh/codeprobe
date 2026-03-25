import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json
from guardrails.schemas import PriorityActionsOutput, LearningPathOutput, clamp_score
from .graphs.report_graph import run_report_graph

DEFAULT_WEIGHTS = {
    "code_quality": 0.15,
    "security": 0.15,
    "architecture": 0.10,
    "frontend": 0.10,
    "backend": 0.10,
    "testing": 0.10,
    "performance": 0.10,
    "documentation": 0.05,
    "accessibility": 0.05,
    "originality": 0.05,
    "requirements": 0.05,
}

GRADE_THRESHOLDS = [
    (9.0, "A"),
    (7.0, "B"),
    (5.0, "C"),
    (3.0, "D"),
    (0.0, "F"),
]


def _grade(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


class ReportAgent(AgentBase):
    agent_id = "report"
    agent_name = "Report Generator"
    phase = 4

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Collecting agent results and computing scores...")

        # --- Collect scores ---
        react_eval = state.get("react_evaluation") or {}
        fastapi_eval = state.get("fastapi_evaluation") or {}
        integration_analysis = state.get("integration_analysis") or {}
        functional_validation = state.get("functional_validation")
        structure_analysis = state.get("structure_analysis") or {}

        security_scan = state.get("security_scan") or {}
        code_smells = state.get("code_smells") or {}
        complexity_report = state.get("complexity_report") or {}
        performance_profile = state.get("performance_profile") or {}
        test_coverage = state.get("test_coverage") or {}
        dependency_audit = state.get("dependency_audit") or {}
        accessibility_report = state.get("accessibility_report") or {}
        documentation_review = state.get("documentation_review") or state.get("documentation_report") or {}

        originality_report = state.get("originality_report") or {}
        originality_score = float(originality_report.get("originality_score", 5.0))

        react_score = float(react_eval.get("score", 5.0))
        fastapi_score = float(fastapi_eval.get("score", 5.0))
        integration_score = float(integration_analysis.get("score", 5.0))
        structure_score = self._compute_structure_score(structure_analysis)
        requirements_score = float(
            functional_validation.get("summary", {}).get("score", 5.0)
            if functional_validation else 5.0
        )
        security_score = float(security_scan.get("security_score", 5.0))
        code_smells_score = float(code_smells.get("code_quality_score", 5.0))
        complexity_score = float(complexity_report.get("complexity_score", 5.0))
        performance_score = float(performance_profile.get("performance_score", 5.0))
        testing_score = float(test_coverage.get("testing_score", 5.0))
        documentation_score = float(documentation_review.get("documentation_score", 5.0))
        accessibility_score = float(accessibility_report.get("accessibility_score", 5.0))

        # Apply scoring weights: rubric > profile custom_weights > defaults
        profile_config = state.get("profile_config") or {}
        custom_weights = profile_config.get("scoring_weights") or {}

        rubric_config = state.get("rubric_config") or {}
        rubric_categories = rubric_config.get("categories", [])
        # Normalize rubric category names to internal keys (e.g. "Code Quality" -> "code_quality")
        rubric_weights = {
            cat["name"].lower().replace(" ", "_"): float(cat["weight"])
            for cat in rubric_categories
            if cat.get("name") and cat.get("weight") is not None
        }
        # Normalize rubric weights to sum to 1.0 if provided
        if rubric_weights:
            total = sum(rubric_weights.values())
            if total > 0 and abs(total - 1.0) > 0.01:
                rubric_weights = {k: v / total for k, v in rubric_weights.items()}

        def _weight(cat: str) -> float:
            if rubric_weights and cat in rubric_weights:
                return rubric_weights[cat]
            if custom_weights and cat in custom_weights:
                return float(custom_weights[cat])
            return DEFAULT_WEIGHTS.get(cat, 0.05)

        # Build category scores
        # code_quality blends react, fastapi, smells, and complexity
        code_quality = round((react_score + fastapi_score + code_smells_score + complexity_score) / 4, 2)
        architecture = round((structure_score + integration_score) / 2, 2)

        category_scores = {
            "code_quality":   {"score": code_quality,        "weight": _weight("code_quality")},
            "security":       {"score": security_score,      "weight": _weight("security")},
            "architecture":   {"score": architecture,        "weight": _weight("architecture")},
            "frontend":       {"score": react_score,         "weight": _weight("frontend")},
            "backend":        {"score": fastapi_score,       "weight": _weight("backend")},
            "testing":        {"score": testing_score,       "weight": _weight("testing")},
            "performance":    {"score": performance_score,   "weight": _weight("performance")},
            "documentation":  {"score": documentation_score, "weight": _weight("documentation")},
            "accessibility":  {"score": accessibility_score, "weight": _weight("accessibility")},
            "originality":    {"score": originality_score,   "weight": _weight("originality")},
            "requirements":   {"score": requirements_score,  "weight": _weight("requirements")},
        }

        # Compute weighted overall
        overall_score = sum(
            v["score"] * v["weight"]
            for v in category_scores.values()
        )
        overall_score = round(clamp_score(overall_score), 2)

        # Add weighted field
        for cat, v in category_scores.items():
            v["weighted"] = round(v["score"] * v["weight"], 3)

        grade = _grade(overall_score)

        self.emit(queue, "progress", f"Overall score: {overall_score}/10 ({grade})")

        # --- Aggregate all findings ---
        all_findings = self._aggregate_findings(state)

        # --- Multi-pass critic: filter false positives (skip in quick mode) ---
        if not state.get("quick_mode", False):
            self.emit(queue, "progress", "Running critic pass to filter false positives...")
            strictness = profile_config.get("strictness", "moderate")
            all_findings = await run_report_graph(
                findings=all_findings,
                strictness=strictness,
                queue=queue,
            )

        # --- Build code heatmap ---
        code_heatmap = self._build_heatmap(all_findings)

        # --- LLM Calls ---
        student_name = state.get("student_name") or "Student"
        profile_id = state.get("profile_id", "bootcamp")

        self.emit(queue, "progress", "Generating executive summary...")
        executive_summary = await self._llm_executive_summary(
            student_name, overall_score, grade, category_scores, all_findings, state, queue
        )

        self.emit(queue, "progress", "Generating priority actions...")
        priority_actions = await self._llm_priority_actions(
            all_findings, category_scores, student_name, queue
        )

        self.emit(queue, "progress", "Generating learning path...")
        learning_path = await self._llm_learning_path(
            category_scores, student_name, queue
        )

        # --- Compute duration ---
        start_time = state.get("_start_time", time.time())
        duration_seconds = round(time.time() - start_time, 1)

        # --- Separate findings by severity ---
        critical_findings = [f for f in all_findings if f.get("type") == "error"]
        suggestions = [f for f in all_findings if f.get("type") == "suggestion"]
        strengths = self._collect_strengths(state)

        report = {
            "meta": {
                "session_id": state.get("session_id"),
                "student_name": student_name,
                "project_id": state.get("project_id"),
                "version": 1,
                "profile": profile_id,
                "rubric": rubric_config.get("name") if rubric_config else None,
                "rubric_id": rubric_config.get("id") if rubric_config else None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "review_duration_seconds": duration_seconds,
                "file_count": state.get("file_count", 0),
            },
            "scores": {
                "overall": overall_score,
                "grade": grade,
                "categories": category_scores,
            },
            "executive_summary": executive_summary,
            "priority_actions": priority_actions,
            "findings": {
                "critical": critical_findings[:20],
                "suggestions": suggestions[:20],
                "strengths": strengths[:10],
            },
            "agents": {
                "react_evaluation": react_eval,
                "fastapi_evaluation": fastapi_eval,
                "integration_analysis": integration_analysis,
                "functional_validation": functional_validation,
                "structure_analysis": structure_analysis,
                "security_scan": security_scan,
                "code_smells": code_smells,
                "complexity_report": complexity_report,
                "performance_profile": performance_profile,
                "test_coverage": test_coverage,
                "dependency_audit": dependency_audit,
                "accessibility_report": accessibility_report,
                "documentation_review": documentation_review,
                "originality_report": originality_report,
            },
            "learning_path": learning_path,
            "code_heatmap": code_heatmap[:20],
        }

        self.emit(queue, "result", data={"overall_score": overall_score, "grade": grade})

        return {**state, "report": report}

    def _compute_structure_score(self, structure_analysis: Dict) -> float:
        """Compute structure score from folder checks."""
        folder_checks = structure_analysis.get("folder_checks", {})
        if not folder_checks:
            return 5.0

        total_checks = 0
        passed_checks = 0

        for section_checks in folder_checks.values():
            for check_name, passed in section_checks.items():
                total_checks += 1
                if passed:
                    passed_checks += 1

        if total_checks == 0:
            return 5.0

        ratio = passed_checks / total_checks
        score = 3.0 + ratio * 7.0  # Range: 3.0 to 10.0
        return round(score, 2)

    def _aggregate_findings(self, state: Dict[str, Any]) -> List[Dict]:
        """Collect all findings from all agent outputs, sorted by severity."""
        all_findings = []

        # React findings
        react_eval = state.get("react_evaluation") or {}
        for f in react_eval.get("findings", []):
            f["source"] = "react"
            all_findings.append(f)

        # FastAPI findings
        fastapi_eval = state.get("fastapi_evaluation") or {}
        for f in fastapi_eval.get("findings", []):
            f["source"] = "fastapi"
            all_findings.append(f)

        # Integration findings
        integration = state.get("integration_analysis") or {}
        llm_int = integration.get("llm_analysis") or {}
        for f in llm_int.get("findings", []):
            f["source"] = "integration"
            all_findings.append(f)

        # Requirements validation gaps
        functional = state.get("functional_validation") or {}
        gap_analysis = functional.get("gap_analysis") or {}
        for gap in gap_analysis.get("critical_gaps", []):
            all_findings.append({
                "type": "error",
                "area": "requirements",
                "detail": f"Missing requirement: {gap.get('description', '')}",
                "file": "",
                "source": "requirements",
            })
        for gap in gap_analysis.get("partial_implementations", []):
            all_findings.append({
                "type": "warning",
                "area": "requirements",
                "detail": f"Partial implementation: {gap.get('description', '')}",
                "file": "",
                "source": "requirements",
            })

        # Security findings
        security_scan = state.get("security_scan") or {}
        for f in security_scan.get("findings", []):
            finding = dict(f)
            finding["source"] = "security"
            # Map severity to type for consistency
            sev = finding.get("severity", "low")
            if sev == "critical":
                finding["type"] = "error"
            elif sev == "high":
                finding["type"] = "error"
            elif sev == "medium":
                finding["type"] = "warning"
            else:
                finding.setdefault("type", "suggestion")
            all_findings.append(finding)

        # Code smell findings
        code_smells = state.get("code_smells") or {}
        for f in code_smells.get("findings", []):
            finding = dict(f)
            finding["source"] = "codesmell"
            finding.setdefault("type", "suggestion")
            all_findings.append(finding)
        # Also add raw smell entries as suggestions
        for smell in code_smells.get("smells", []):
            sev = smell.get("severity", "low")
            f_type = "warning" if sev in ("high", "medium") else "suggestion"
            all_findings.append({
                "type": f_type,
                "area": smell.get("type", "code_smell"),
                "detail": smell.get("detail", ""),
                "file": smell.get("file", ""),
                "source": "codesmell",
            })

        # Complexity findings
        complexity_report = state.get("complexity_report") or {}
        for f in complexity_report.get("findings", []):
            finding = dict(f)
            finding["source"] = "complexity"
            finding.setdefault("type", "suggestion")
            all_findings.append(finding)

        # Performance findings
        performance_profile = state.get("performance_profile") or {}
        for f in performance_profile.get("findings", []):
            finding = dict(f)
            finding["source"] = "performance"
            finding.setdefault("type", "suggestion")
            all_findings.append(finding)

        # Test coverage findings
        test_coverage = state.get("test_coverage") or {}
        for f in test_coverage.get("findings", []):
            finding = dict(f)
            finding["source"] = "testcoverage"
            finding.setdefault("type", "suggestion")
            all_findings.append(finding)

        # Dependency audit findings
        dependency_audit = state.get("dependency_audit") or {}
        for f in dependency_audit.get("findings", []):
            finding = dict(f)
            finding["source"] = "dependencies"
            finding.setdefault("type", "suggestion")
            all_findings.append(finding)

        # Accessibility findings
        accessibility_report = state.get("accessibility_report") or {}
        for f in accessibility_report.get("findings", []):
            finding = dict(f)
            finding["source"] = "accessibility"
            finding.setdefault("type", "suggestion")
            all_findings.append(finding)

        # Documentation findings
        documentation_report = state.get("documentation_review") or state.get("documentation_report") or {}
        for f in documentation_report.get("findings", []):
            finding = dict(f)
            finding["source"] = "documentation"
            finding.setdefault("type", "suggestion")
            all_findings.append(finding)

        # Originality findings
        for f in (state.get("originality_report") or {}).get("findings", []):
            all_findings.append(f)

        # Sort: errors first, then warnings, then suggestions
        severity_order = {"error": 0, "warning": 1, "suggestion": 2}
        all_findings.sort(key=lambda f: severity_order.get(f.get("type", "suggestion"), 2))

        return all_findings

    def _collect_strengths(self, state: Dict[str, Any]) -> List[str]:
        """Collect strengths from all agent outputs."""
        strengths = []

        react_eval = state.get("react_evaluation") or {}
        llm_react = react_eval.get("llm_analysis") or {}
        strengths.extend(llm_react.get("strengths", []))

        fastapi_eval = state.get("fastapi_evaluation") or {}
        llm_fastapi = fastapi_eval.get("llm_analysis") or {}
        strengths.extend(llm_fastapi.get("strengths", []))

        performance_profile = state.get("performance_profile") or {}
        if float(performance_profile.get("performance_score", 0.0)) > 7.0:
            strengths.append("Good performance practices: no major N+1 queries, re-render traps, or blocking I/O detected")

        test_coverage = state.get("test_coverage") or {}
        if float(test_coverage.get("testing_score", 0.0)) > 7.0:
            strengths.append("Strong test coverage with meaningful assertions and critical paths covered")

        dependency_audit = state.get("dependency_audit") or {}
        if float(dependency_audit.get("dependency_score", 0.0)) > 7.0:
            strengths.append("Healthy dependency tree: no deprecated or high-risk packages detected")

        accessibility_report = state.get("accessibility_report") or {}
        if float(accessibility_report.get("accessibility_score", 0.0)) > 7.0:
            strengths.append("Good accessibility compliance: images have alt text, inputs have labels, WCAG A violations minimal")

        documentation_review = state.get("documentation_review") or {}
        if float(documentation_review.get("documentation_score", 0.0)) > 7.0:
            strengths.append("Well-documented codebase: README present with setup instructions and good inline comment density")

        originality_report = state.get("originality_report") or {}
        originality_score = float(originality_report.get("originality_score", 0.0))
        if originality_score > 7.0:
            strengths.append({"type": "strength", "message": f"High originality ({originality_score:.1f}/10) — genuinely original work detected"})

        return strengths

    def _build_heatmap(self, all_findings: List[Dict]) -> List[Dict]:
        """Build a code heatmap showing files with most issues."""
        file_stats: Dict[str, Dict] = {}

        for finding in all_findings:
            file_path = finding.get("file", "")
            if not file_path:
                continue
            if file_path not in file_stats:
                file_stats[file_path] = {"file": file_path, "issue_count": 0, "severity_sum": 0}
            file_stats[file_path]["issue_count"] += 1
            severity_map = {"error": 3, "warning": 2, "suggestion": 1}
            file_stats[file_path]["severity_sum"] += severity_map.get(finding.get("type", "suggestion"), 1)

        heatmap = list(file_stats.values())
        heatmap.sort(key=lambda x: x["severity_sum"], reverse=True)
        return heatmap

    async def _llm_executive_summary(
        self,
        student_name: str,
        overall_score: float,
        grade: str,
        category_scores: Dict,
        all_findings: List[Dict],
        state: Dict[str, Any],
        queue: asyncio.Queue,
    ) -> str:
        """Generate executive summary using LLM."""
        # Build context
        score_summary = ", ".join(
            f"{cat}: {v['score']}/10"
            for cat, v in category_scores.items()
        )
        top_findings = [
            f.get("detail", "")
            for f in all_findings[:5]
            if f.get("type") == "error"
        ]
        structure = state.get("structure_analysis", {})
        frameworks = structure.get("fe_frameworks", []) + structure.get("be_frameworks", [])

        rubric_config = state.get("rubric_config") or {}
        rubric_categories = rubric_config.get("categories", [])
        rubric_lines = ""
        if rubric_categories:
            expectations = [
                f"- {cat['name']}: {cat['min_expectations']}"
                for cat in rubric_categories
                if cat.get("min_expectations")
            ]
            if expectations:
                rubric_lines = "\nRubric Requirements:\n" + "\n".join(expectations)

        profile_config = state.get("profile_config") or {}
        tone = profile_config.get("llm_tone", "constructive and direct")
        strictness = profile_config.get("strictness", "moderate")

        prompt = f"""Write an executive code review summary for a student.

Student: {student_name}
Overall Score: {overall_score}/10 (Grade: {grade})
Tech Stack: {', '.join(frameworks) or 'Unknown'}
Category Scores: {score_summary}
Top Issues: {'; '.join(top_findings) or 'None identified'}
Review Tone: {tone}
Strictness Level: {strictness}{rubric_lines}

Write 3-4 paragraphs addressing the student directly (use "you" and "your").
Be {tone}. Cover: overall assessment, strengths, key areas for improvement, next steps.
Do NOT return JSON — return plain text paragraphs only."""

        try:
            response = await ollama_chat(prompt, timeout=120)
            if response and len(response.strip()) > 50:
                return response.strip()
        except Exception as e:
            self.emit(queue, "progress", f"Executive summary LLM failed: {e}")

        # Fallback
        return (
            f"Your project received an overall score of {overall_score}/10 (Grade: {grade}). "
            f"The review analyzed {state.get('file_count', 0)} files across your codebase. "
            "Please review the detailed findings below for specific areas of improvement. "
            "Focus on addressing the critical issues first, then work through the warnings and suggestions."
        )

    async def _llm_priority_actions(
        self,
        all_findings: List[Dict],
        category_scores: Dict,
        student_name: str,
        queue: asyncio.Queue,
    ) -> List[Dict]:
        """Generate top 5 priority actions with specific instructions."""
        # Find lowest-scoring categories
        lowest_cats = sorted(
            [(cat, v["score"]) for cat, v in category_scores.items()],
            key=lambda x: x[1]
        )[:3]

        errors = [f for f in all_findings if f.get("type") == "error"][:10]
        warnings = [f for f in all_findings if f.get("type") == "warning"][:5]

        findings_text = json.dumps(errors + warnings, default=str)[:2000]

        prompt = f"""Generate the top 5 priority actions for a student to improve their code.

Lowest scoring categories: {', '.join(f"{c}: {s}/10" for c, s in lowest_cats)}
Key findings: {findings_text}

Return ONLY valid JSON:
{{
  "actions": [
    {{
      "rank": 1,
      "severity": "critical|high|medium|low",
      "title": "Short action title",
      "detail": "Specific instructions on what to fix and how",
      "file": "specific file if applicable",
      "estimated_hours": 2.0,
      "category": "category name"
    }}
  ]
}}

Be specific — include exact code patterns, file names, or line references where possible."""

        try:
            response = await ollama_chat(prompt, timeout=120)
            parsed = parse_llm_json(response, default=None)
            if parsed and isinstance(parsed, dict):
                validated = self.validate_output(parsed, PriorityActionsOutput, queue)
                actions = validated.get("actions", [])
                if actions:
                    return actions[:5]
        except Exception as e:
            self.emit(queue, "progress", f"Priority actions LLM failed: {e}")

        # Fallback: generate from raw findings
        fallback = []
        for i, finding in enumerate(errors[:5], start=1):
            fallback.append({
                "rank": i,
                "severity": "high",
                "title": finding.get("detail", "Fix identified issue")[:60],
                "detail": finding.get("fix_hint") or finding.get("detail", "Review and fix this issue"),
                "file": finding.get("file", ""),
                "estimated_hours": 1.0,
                "category": finding.get("area", "general"),
            })
        return fallback

    async def _llm_learning_path(
        self,
        category_scores: Dict,
        student_name: str,
        queue: asyncio.Queue,
    ) -> Dict:
        """Generate a 2-week learning path based on lowest-scoring categories."""
        lowest_cats = sorted(
            [(cat, v["score"]) for cat, v in category_scores.items()],
            key=lambda x: x[1]
        )[:4]

        prompt = f"""Create a personalized 2-week learning plan for {student_name} based on their code review results.

Lowest scoring areas needing most improvement:
{chr(10).join(f"- {cat}: {score:.1f}/10" for cat, score in lowest_cats)}

Return ONLY valid JSON matching exactly this structure:
{{
  "weeks": [
    {{
      "week": 1,
      "focus": "<area name>",
      "items": [
        {{
          "day": "1-2",
          "topic": "<specific topic>",
          "why": "<1 sentence why this matters given their code>",
          "exercise": "<concrete hands-on task they should do>",
          "estimated_hours": <integer 1-4>
        }}
      ]
    }},
    {{
      "week": 2,
      "focus": "<area name>",
      "items": [
        {{
          "day": "1-2",
          "topic": "<specific topic>",
          "why": "<why it matters>",
          "exercise": "<concrete task>",
          "estimated_hours": <integer 1-4>
        }}
      ]
    }}
  ],
  "skill_gaps": {{
    "<category>": <score as number>,
    ...include all lowest scoring categories
  }}
}}"""

        try:
            response = await ollama_chat(prompt, timeout=120)
            parsed = parse_llm_json(response, default=None)
            if parsed and isinstance(parsed, dict):
                return self.validate_output(parsed, LearningPathOutput, queue)
        except Exception as e:
            self.emit(queue, "progress", f"Learning path LLM failed: {e}")

        # Fallback
        return {
            "weeks": [
                {
                    "week": 1,
                    "focus": lowest_cats[0][0] if lowest_cats else "code_quality",
                    "items": [
                        {
                            "day": "1-3",
                            "topic": f"Improve {lowest_cats[0][0].replace('_', ' ').title()}" if lowest_cats else "Code Quality",
                            "why": f"This area scored {lowest_cats[0][1]:.1f}/10 in your review" if lowest_cats else "Your review flagged quality issues",
                            "exercise": "Review all flagged issues in this category and apply the suggested fixes one by one",
                            "estimated_hours": 3,
                        }
                    ],
                },
                {
                    "week": 2,
                    "focus": lowest_cats[1][0] if len(lowest_cats) > 1 else "testing",
                    "items": [
                        {
                            "day": "1-3",
                            "topic": f"Improve {lowest_cats[1][0].replace('_', ' ').title()}" if len(lowest_cats) > 1 else "Testing",
                            "why": f"This area scored {lowest_cats[1][1]:.1f}/10 in your review" if len(lowest_cats) > 1 else "Testing coverage was low",
                            "exercise": "Write unit tests for the main functions identified as untested",
                            "estimated_hours": 3,
                        }
                    ],
                },
            ],
            "skill_gaps": {cat: round(score, 1) for cat, score in lowest_cats},
        }
