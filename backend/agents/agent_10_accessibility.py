import asyncio
import re
from typing import Any, Dict, List
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json
from guardrails.schemas import AccessibilityLLMOutput


# WCAG level mapping for check types
WCAG_LEVELS = {
    "img_no_alt": "A",
    "button_no_text": "A",
    "input_no_label": "A",
    "missing_lang": "A",
    "heading_hierarchy": "AA",
    "low_contrast": "AA",
    "interactive_div": "AA",
    "aria_live_missing": "AA",
}

# Severity based on WCAG level
WCAG_SEVERITY = {
    "A": "critical",
    "AA": "serious",
}


class AccessibilityAgent(AgentBase):
    agent_id = "accessibility"
    agent_name = "Accessibility Checker"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Running accessibility static checks...")

        frontend_files = state.get("frontend_files", {})

        if not frontend_files:
            self.emit(queue, "progress", "No frontend files found, skipping accessibility check")
            return {
                **state,
                "accessibility_report": {
                    "violations": [],
                    "wcag_summary": {"A": "pass", "AA": "pass"},
                    "findings": [],
                    "accessibility_score": 5.0,
                },
            }

        static_violations = self._static_checks(frontend_files)

        critical_count = sum(1 for v in static_violations if v.get("impact") == "critical")
        serious_count = sum(1 for v in static_violations if v.get("impact") == "serious")
        moderate_count = sum(1 for v in static_violations if v.get("impact") == "moderate")

        self.emit(
            queue,
            "progress",
            f"Accessibility static scan: {len(static_violations)} violations "
            f"(critical={critical_count}, serious={serious_count}, moderate={moderate_count})",
        )

        # LLM analysis — send 4 main component files
        llm_result = await self._llm_analysis(frontend_files, queue)
        llm_violations = llm_result.get("violations", [])
        wcag_summary = llm_result.get("wcag_summary", {})

        # Merge all violations
        all_violations = static_violations + [
            v for v in llm_violations if isinstance(v, dict)
        ]

        # Recompute counts with merged results
        critical_count = sum(1 for v in all_violations if v.get("impact") == "critical")
        serious_count = sum(1 for v in all_violations if v.get("impact") == "serious")
        moderate_count = sum(1 for v in all_violations if v.get("impact") == "moderate")

        # Compute WCAG summary if LLM didn't provide one
        if not wcag_summary:
            wcag_summary = self._compute_wcag_summary(static_violations)

        # Score: 10 - (critical * 2 + serious * 1 + moderate * 0.5)
        score = 10.0 - (critical_count * 2 + serious_count * 1 + moderate_count * 0.5)
        score = round(max(0.0, min(10.0, score)), 2)

        # Build findings
        findings: List[Dict] = []
        for v in all_violations:
            impact = v.get("impact", "moderate")
            findings.append({
                "type": "error" if impact == "critical" else "warning" if impact == "serious" else "suggestion",
                "area": "Accessibility",
                "detail": v.get("rule", v.get("detail", "Accessibility violation")),
                "file": v.get("file", ""),
                "fix_hint": v.get("fix", v.get("fix_hint", "")),
            })

        self.emit(queue, "result", data={"score": score})

        return {
            **state,
            "accessibility_report": {
                "violations": all_violations,
                "wcag_summary": wcag_summary,
                "findings": findings,
                "accessibility_score": score,
            },
        }

    def _static_checks(self, frontend_files: Dict[str, Any]) -> List[Dict]:
        violations: List[Dict] = []

        # Track heading levels across all files for hierarchy check
        h1_seen = False
        h2_seen = False
        h3_seen = False
        heading_file = ""

        for file_path, entry in frontend_files.items():
            content = entry.get("content", "")
            if not content:
                continue

            # 1. Images without alt attribute
            # Match <img ... > tags that don't contain alt=
            img_matches = re.findall(r"<img\b(?:[^>](?!alt=))*>", content, re.DOTALL)
            # Simpler and more reliable: find all img tags, check each for alt=
            for img_tag in re.findall(r"<img\b[^>]*>", content, re.IGNORECASE):
                if "alt=" not in img_tag:
                    violations.append({
                        "rule": "img-alt",
                        "impact": "critical",
                        "element": img_tag[:80],
                        "file": file_path,
                        "fix": "Add alt attribute to all <img> elements: alt='description' or alt='' for decorative images",
                    })

            # 2. Buttons without visible text
            for btn_tag in re.findall(r"<button\b[^>]*>\s*</button>", content, re.IGNORECASE):
                violations.append({
                    "rule": "button-name",
                    "impact": "critical",
                    "element": btn_tag[:80],
                    "file": file_path,
                    "fix": "Add visible text or aria-label to all <button> elements",
                })

            # Empty anchor tags
            for a_tag in re.findall(r"<a\b[^>]*>\s*</a>", content, re.IGNORECASE):
                violations.append({
                    "rule": "link-name",
                    "impact": "critical",
                    "element": a_tag[:80],
                    "file": file_path,
                    "fix": "Add visible text or aria-label to all <a> elements",
                })

            # 3. Interactive divs without role
            for div_match in re.finditer(r"<div\b([^>]*)>", content, re.IGNORECASE):
                attrs = div_match.group(1)
                if "onClick" in attrs and "role=" not in attrs:
                    violations.append({
                        "rule": "interactive-element-affordance",
                        "impact": "serious",
                        "element": div_match.group(0)[:80],
                        "file": file_path,
                        "fix": "Add role='button' and tabIndex={0} to interactive <div> elements, or use <button>",
                    })

            # 4. Inputs without labels
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if re.search(r"<input\b", line, re.IGNORECASE):
                    # Check if aria-label is on the same line
                    if "aria-label" not in line and "aria-labelledby" not in line:
                        # Check surrounding lines for <label
                        context_start = max(0, i - 3)
                        context_end = min(len(lines), i + 2)
                        context = "\n".join(lines[context_start:context_end])
                        if "<label" not in context and "htmlFor" not in context:
                            violations.append({
                                "rule": "label",
                                "impact": "critical",
                                "element": line.strip()[:80],
                                "file": file_path,
                                "fix": "Associate a <label> with htmlFor or add aria-label to the <input>",
                            })

            # 5. Missing lang on html element
            if file_path.endswith(".html"):
                for html_tag in re.findall(r"<html\b[^>]*>", content, re.IGNORECASE):
                    if "lang=" not in html_tag:
                        violations.append({
                            "rule": "html-has-lang",
                            "impact": "critical",
                            "element": html_tag[:80],
                            "file": file_path,
                            "fix": "Add lang attribute to <html> element: <html lang='en'>",
                        })

            # 6. Track heading levels for hierarchy check
            if re.search(r"<h1[\s>]", content, re.IGNORECASE):
                h1_seen = True
                heading_file = file_path
            if re.search(r"<h2[\s>]", content, re.IGNORECASE):
                h2_seen = True
            if re.search(r"<h3[\s>]", content, re.IGNORECASE):
                h3_seen = True

            # 7. Missing aria-live: setState that updates visible content
            if re.search(r"setState\s*\(", content) and not re.search(r"aria-live", content):
                violations.append({
                    "rule": "aria-live-region",
                    "impact": "moderate",
                    "element": "",
                    "file": file_path,
                    "fix": "Add aria-live='polite' to regions that update dynamically so screen readers announce changes",
                })

            # 8. Low contrast inline colors (heuristic: light hex colors)
            for color_match in re.finditer(r"color:\s*#([89a-fA-F][0-9a-fA-F]{5})", content):
                violations.append({
                    "rule": "color-contrast",
                    "impact": "serious",
                    "element": color_match.group(0)[:80],
                    "file": file_path,
                    "fix": "Verify color contrast ratio is at least 4.5:1 for normal text (WCAG AA)",
                })

        # Heading hierarchy: h1 present, h2 absent, h3 present
        if h1_seen and h3_seen and not h2_seen:
            violations.append({
                "rule": "heading-order",
                "impact": "serious",
                "element": "h1 → h3 (h2 skipped)",
                "file": heading_file,
                "fix": "Do not skip heading levels — use h1, h2, h3 in order",
            })

        return violations

    def _compute_wcag_summary(self, violations: List[Dict]) -> Dict[str, str]:
        a_rules = {"img-alt", "button-name", "link-name", "label", "html-has-lang"}
        aa_rules = {"heading-order", "color-contrast", "interactive-element-affordance"}

        a_violations = [v for v in violations if v.get("rule") in a_rules]
        aa_violations = [v for v in violations if v.get("rule") in aa_rules]

        return {
            "A": "fail" if a_violations else "pass",
            "AA": "fail" if aa_violations else "pass",
        }

    async def _llm_analysis(
        self, frontend_files: Dict[str, Any], queue: asyncio.Queue
    ) -> Dict:
        self.emit(queue, "progress", "Running LLM accessibility analysis on component files...")

        # Select 4 main component files (largest by size, preferring .tsx/.jsx)
        component_files = {
            path: entry
            for path, entry in frontend_files.items()
            if path.endswith((".tsx", ".jsx", ".js", ".ts"))
        }
        sorted_components = sorted(
            component_files.items(), key=lambda x: x[1].get("size", 0), reverse=True
        )[:4]

        if not sorted_components:
            # Fall back to any frontend files
            sorted_fe = sorted(
                frontend_files.items(), key=lambda x: x[1].get("size", 0), reverse=True
            )[:4]
            sorted_components = sorted_fe

        file_sections = []
        total_chars = 0
        max_chars = 5000

        for path, entry in sorted_components:
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
        if not combined.strip():
            return {}

        prompt = f"""Review these React components for WCAG 2.1 AA accessibility compliance. Focus on keyboard navigation, screen reader support, color contrast, and ARIA attributes. Return ONLY valid JSON: {{"violations": [{{"rule": "string", "impact": "critical|serious|moderate", "element": "string", "file": "string", "fix": "string"}}], "wcag_summary": {{"A": "pass|partial|fail", "AA": "pass|partial|fail"}}, "accessibility_score": 0.0}}

{combined}"""

        try:
            response = await ollama_chat(prompt, timeout=180)
            if not response:
                return {}
            parsed = parse_llm_json(response, default=None)
            if not parsed or not isinstance(parsed, dict):
                return {}
            return self.validate_output(parsed, AccessibilityLLMOutput, queue)
        except Exception as e:
            self.emit(queue, "progress", f"LLM accessibility analysis failed: {e}")
            return {}
