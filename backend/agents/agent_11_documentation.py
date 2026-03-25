import asyncio
import re
from typing import Any, Dict, List, Optional
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json
from guardrails.schemas import DocumentationLLMOutput


class DocumentationAgent(AgentBase):
    agent_id = "documentation"
    agent_name = "Documentation Reviewer"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Analyzing project documentation...")

        config_files = state.get("config_files", {})
        frontend_files = state.get("frontend_files", {})
        backend_files = state.get("backend_files", {})
        all_files = {**config_files, **frontend_files, **backend_files}

        # 1. README checks
        readme_content, readme_path = self._find_readme(all_files)
        readme_checks = self._check_readme(readme_content)
        readme_score = sum(2 for v in readme_checks.values() if v)  # 2 pts each, max 10

        # 2. Python docstring coverage
        py_ratio = self._python_docstring_ratio(backend_files)

        # 3. TypeScript JSDoc coverage
        ts_ratio = self._ts_jsdoc_ratio(frontend_files)

        # 4. FastAPI endpoint documentation ratio
        fastapi_ratio = self._fastapi_endpoint_doc_ratio(backend_files)

        self.emit(
            queue,
            "progress",
            f"Documentation: readme_score={readme_score}, "
            f"py_docstring={py_ratio:.2f}, ts_jsdoc={ts_ratio:.2f}, fastapi={fastapi_ratio:.2f}",
        )

        # Weighted scoring
        # README: 40%, Python docstrings: 30%, TS JSDoc: 20%, FastAPI docs: 10%
        score = (
            readme_score * 0.40
            + py_ratio * 10 * 0.30
            + ts_ratio * 10 * 0.20
            + fastapi_ratio * 10 * 0.10
        )
        score = round(max(0.0, min(10.0, score)), 2)

        # Build findings
        findings: List[Dict] = []
        if not readme_checks.get("exists"):
            findings.append({
                "type": "error",
                "area": "Documentation",
                "detail": "README.md is missing",
                "file": "",
                "fix_hint": "Create a README.md with project description, setup instructions, and usage examples",
            })
        else:
            for section, present in readme_checks.items():
                if not present and section != "exists":
                    findings.append({
                        "type": "suggestion",
                        "area": "Documentation",
                        "detail": f"README missing section: {section.replace('_', ' ')}",
                        "file": readme_path or "README.md",
                        "fix_hint": f"Add a {section.replace('_', ' ')} section to the README",
                    })

        if py_ratio < 0.5 and backend_files:
            findings.append({
                "type": "suggestion",
                "area": "Documentation",
                "detail": f"Low Python docstring coverage: {py_ratio:.0%} of functions documented",
                "file": "",
                "fix_hint": "Add docstrings to all public functions and classes",
            })

        if ts_ratio < 0.5 and frontend_files:
            findings.append({
                "type": "suggestion",
                "area": "Documentation",
                "detail": f"Low TypeScript JSDoc coverage: {ts_ratio:.0%} of exports documented",
                "file": "",
                "fix_hint": "Add JSDoc comments (/** ... */) above exported functions and components",
            })

        # LLM analysis — send README + 2 key files
        llm_context = self.get_llm_context(state)
        llm_result = await self._llm_analysis(readme_content, readme_path, all_files, queue, llm_context)
        missing_sections = llm_result.get("missing_sections", [])
        for section in missing_sections:
            if isinstance(section, str):
                findings.append({
                    "type": "suggestion",
                    "area": "Documentation",
                    "detail": f"LLM: Missing documentation section: {section}",
                    "file": readme_path or "README.md",
                    "fix_hint": f"Add '{section}' to the README or inline docs",
                })

        docstring_coverage = {
            "python_ratio": py_ratio,
            "typescript_ratio": ts_ratio,
            "fastapi_ratio": fastapi_ratio,
        }

        self.emit(queue, "result", data={"score": score})

        return {
            **state,
            "documentation_review": {
                "readme_checks": readme_checks,
                "readme_found": readme_checks.get("exists", False),
                "readme_score": float(readme_score),
                "python_doc_ratio": py_ratio,
                "js_doc_ratio": ts_ratio,
                "comment_density": 0.0,
                "docstring_coverage": docstring_coverage,
                "findings": findings,
                "documentation_score": score,
                "llm_assessment": llm_result.get("improvement_suggestions", []),
            },
        }

    def _find_readme(self, all_files: Dict[str, Any]) -> tuple:
        """Find README.md in the file set. Returns (content, path)."""
        # Priority: root README.md
        for path, entry in all_files.items():
            basename = path.split("/")[-1].lower()
            if basename == "readme.md":
                return entry.get("content", ""), path
        return "", ""

    def _check_readme(self, content: str) -> Dict[str, bool]:
        checks = {
            "exists": bool(content),
            "has_description": False,
            "has_setup": False,
            "has_usage_examples": False,
            "has_env_vars": False,
            "has_api_docs": False,
        }
        if not content:
            return checks

        # Has description: check first 200 chars for non-trivial content
        checks["has_description"] = len(content[:200].strip()) > 30

        # Has setup/installation
        checks["has_setup"] = bool(
            re.search(r"##?\s*(install|setup|getting started|requirements|npm|pip)", content, re.IGNORECASE)
        )

        # Has usage examples: code blocks
        checks["has_usage_examples"] = "```" in content

        # Has env vars docs
        checks["has_env_vars"] = bool(
            re.search(r"\.env|[A-Z_]{3,}=|environment variable", content, re.IGNORECASE)
        )

        # Has API docs
        checks["has_api_docs"] = bool(
            re.search(r"##?\s*(api|endpoint|route|swagger|openapi)", content, re.IGNORECASE)
        )

        return checks

    def _python_docstring_ratio(self, backend_files: Dict[str, Any]) -> float:
        total_funcs = 0
        documented_funcs = 0

        for file_path, entry in backend_files.items():
            if not file_path.endswith(".py"):
                continue
            content = entry.get("content", "")
            if not content:
                continue

            lines = content.splitlines()
            for i, line in enumerate(lines):
                if re.match(r"\s*def \w+\s*\(", line) or re.match(r"\s*async def \w+\s*\(", line):
                    total_funcs += 1
                    # Check if next non-empty line is a docstring
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        if next_line.startswith('"""') or next_line.startswith("'''"):
                            documented_funcs += 1
                        break

        if total_funcs == 0:
            return 1.0  # No functions found — no penalty
        return round(documented_funcs / total_funcs, 3)

    def _ts_jsdoc_ratio(self, frontend_files: Dict[str, Any]) -> float:
        total_exports = 0
        documented_exports = 0

        for file_path, entry in frontend_files.items():
            if not file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
                continue
            content = entry.get("content", "")
            if not content:
                continue

            lines = content.splitlines()
            for i, line in enumerate(lines):
                if re.search(r"\bexport\b.*(function|class|const|default)", line):
                    total_exports += 1
                    # Check previous non-empty line for JSDoc
                    for j in range(i - 1, max(i - 4, -1), -1):
                        prev_line = lines[j].strip()
                        if not prev_line:
                            continue
                        if prev_line.startswith("/**") or prev_line.startswith("*/") or prev_line.startswith("*"):
                            documented_exports += 1
                        break

        if total_exports == 0:
            return 1.0
        return round(documented_exports / total_exports, 3)

    def _fastapi_endpoint_doc_ratio(self, backend_files: Dict[str, Any]) -> float:
        total_endpoints = 0
        documented_endpoints = 0

        for file_path, entry in backend_files.items():
            if not file_path.endswith(".py"):
                continue
            content = entry.get("content", "")
            if not content:
                continue

            lines = content.splitlines()
            for i, line in enumerate(lines):
                if re.search(r"@(app|router)\.(get|post|put|delete|patch)\s*\(", line):
                    total_endpoints += 1
                    # Check if there's a description= in the decorator or docstring in the function
                    decorator_line = line
                    if "description=" in decorator_line:
                        documented_endpoints += 1
                        continue
                    # Look ahead for docstring in the function body
                    for j in range(i + 1, min(i + 6, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        if re.search(r"^(async\s+)?def\s+\w+", next_line):
                            continue
                        if next_line.startswith('"""') or next_line.startswith("'''"):
                            documented_endpoints += 1
                        break

        if total_endpoints == 0:
            return 1.0
        return round(documented_endpoints / total_endpoints, 3)

    async def _llm_analysis(
        self,
        readme_content: str,
        readme_path: str,
        all_files: Dict[str, Any],
        queue: asyncio.Queue,
        llm_context: str = "",
    ) -> Dict:
        self.emit(queue, "progress", "Running LLM documentation analysis...")

        # Send README + 2 key files
        file_sections = []
        total_chars = 0
        max_chars = 5000

        if readme_content:
            header = f"\n--- {readme_path or 'README.md'} ---\n"
            snippet = readme_content[:2000]
            file_sections.append(header + snippet)
            total_chars += len(header) + len(snippet)

        # Pick 2 key source files (prefer main.py, app.py, index.tsx, App.tsx)
        priority_names = {"main.py", "app.py", "index.tsx", "app.tsx", "index.ts", "app.ts"}
        key_files = []
        for path, entry in all_files.items():
            basename = path.split("/")[-1].lower()
            if basename in priority_names:
                key_files.append((path, entry))
            if len(key_files) >= 2:
                break

        # Fall back to largest files if not enough priority files
        if len(key_files) < 2:
            sorted_all = sorted(all_files.items(), key=lambda x: x[1].get("size", 0), reverse=True)
            for path, entry in sorted_all:
                if not any(path == kf[0] for kf in key_files):
                    key_files.append((path, entry))
                if len(key_files) >= 2:
                    break

        for path, entry in key_files[:2]:
            content = entry.get("content", "")
            header = f"\n--- {path} ---\n"
            available = max_chars - total_chars - len(header) - 100
            if available <= 0:
                break
            snippet = content[:available]
            section = header + snippet
            file_sections.append(section)
            total_chars += len(section)

        combined = "".join(file_sections)
        if not combined.strip():
            return {}

        context_prefix = llm_context + "\n\n" if llm_context else ""
        prompt = f"""{context_prefix}Could a new developer onboard from this documentation alone? What's missing? Return ONLY valid JSON: {{"can_onboard": true, "missing_sections": ["string"], "improvement_suggestions": ["string"], "documentation_score": 0.0}}

{combined}"""

        try:
            response = await ollama_chat(prompt, timeout=180)
            if not response:
                return {}
            parsed = parse_llm_json(response, default=None)
            if not parsed or not isinstance(parsed, dict):
                return {}
            return self.validate_output(parsed, DocumentationLLMOutput, queue)
        except Exception as e:
            self.emit(queue, "progress", f"LLM documentation analysis failed: {e}")
            return {}
