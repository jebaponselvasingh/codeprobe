import asyncio
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json
from guardrails.schemas import TestCoverageLLMOutput


class TestCoverageAgent(AgentBase):
    agent_id = "testcoverage"
    agent_name = "Test Coverage Analyzer"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Analyzing test coverage...")

        frontend_files = state.get("frontend_files", {})
        backend_files = state.get("backend_files", {})
        all_files = {**frontend_files, **backend_files}

        if not all_files:
            self.emit(queue, "progress", "No files found, skipping test coverage analysis")
            return {
                **state,
                "test_coverage": {
                    "test_file_ratio": 0.0,
                    "test_count": 0,
                    "source_count": 0,
                    "critical_gaps": [],
                    "avg_assertions_per_test": 0.0,
                    "missing_tests": [],
                    "findings": [],
                    "testing_score": 5.0,
                },
            }

        # 1. Identify test files vs source files
        test_files: Dict[str, Any] = {}
        source_files: Dict[str, Any] = {}

        test_pattern = re.compile(
            r"(test|spec|__tests__)[^/]*\.(py|ts|tsx|js|jsx)$"
            r"|test_[^/]+\.(py|ts|tsx|js|jsx)$"
            r"|[^/]+_test\.(py|ts|tsx|js|jsx)$",
            re.IGNORECASE,
        )

        for file_path, entry in all_files.items():
            basename = file_path.split("/")[-1]
            name_lower = basename.lower()
            # Match test file patterns
            if (
                re.search(r"test|spec", name_lower)
                or name_lower.startswith("test_")
                or re.search(r"_test\.", name_lower)
                or ".test." in name_lower
                or ".spec." in name_lower
                or "__tests__" in file_path
            ):
                test_files[file_path] = entry
            else:
                source_files[file_path] = entry

        source_count = len(source_files)
        test_count_files = len(test_files)

        # 2. Parse test content
        total_test_functions = 0
        total_assertions = 0
        has_mocks = False
        has_snapshots = False

        for file_path, entry in test_files.items():
            content = entry.get("content", "")
            if not content:
                continue

            # Count test functions
            py_tests = len(re.findall(r"\bdef test_\w+\s*\(", content))
            js_tests = len(re.findall(r"\bit\s*\(|test\s*\(|describe\s*\(", content))
            total_test_functions += py_tests + js_tests

            # Count assertions
            assertions = len(re.findall(
                r"\bassert\b|expect\s*\(|\.toBe\s*\(|assertEqual\s*\(", content
            ))
            total_assertions += assertions

            # Mocks
            if re.search(r"mock|patch|jest\.fn|MagicMock", content, re.IGNORECASE):
                has_mocks = True

            # Snapshots
            if re.search(r"toMatchSnapshot|\.snap", content):
                has_snapshots = True

        test_count = total_test_functions
        avg_assertions = round(total_assertions / max(test_count, 1), 2)

        # 3. Per-module test pairing
        def strip_ext(name: str) -> str:
            for ext in (".py", ".ts", ".tsx", ".js", ".jsx"):
                if name.endswith(ext):
                    return name[: -len(ext)]
            return name

        def base_name(path: str) -> str:
            basename = path.split("/")[-1]
            name = strip_ext(basename)
            # Remove test prefix/suffix
            name = re.sub(r"^test_|_test$|\.test$|\.spec$", "", name, flags=re.IGNORECASE)
            return name.lower()

        source_base_names = {base_name(p): p for p in source_files}
        tested_sources = set()
        for tp in test_files:
            bname = base_name(tp)
            if bname in source_base_names:
                tested_sources.add(source_base_names[bname])

        # 4. Critical path detection
        critical_gaps: List[str] = []
        for file_path, entry in source_files.items():
            content = entry.get("content", "")
            if file_path in tested_sources:
                continue

            is_critical = False
            # Backend: files with route decorators
            if re.search(r"@(app|router)\.(get|post|put|delete|patch)\s*\(", content):
                is_critical = True
            # Auth flows
            bname = file_path.split("/")[-1].lower()
            if re.match(r"(auth|login|register)", bname):
                is_critical = True
            # Frontend: component exports used in routing
            if re.search(r"export\s+(default\s+)?(?:function|class|const)\s+\w+", content):
                if re.search(r"Route|Router|Navigate|Switch", content):
                    is_critical = True

            if is_critical:
                critical_gaps.append(file_path)

        # 5. Parse real coverage reports if present
        temp_dir = state.get("temp_dir", "")
        coverage_data = self._parse_coverage_reports(temp_dir)
        line_coverage_pct = coverage_data.get("line_coverage_pct")
        branch_coverage_pct = coverage_data.get("branch_coverage_pct")
        coverage_source = coverage_data.get("source", "none")

        if line_coverage_pct is not None:
            self.emit(queue, "progress", f"Coverage report found ({coverage_source}): {line_coverage_pct:.1f}% line coverage")

        # 6. Compute score
        test_file_ratio = round(test_count_files / max(source_count, 1), 3)
        if line_coverage_pct is not None:
            # Use actual coverage: 60% weight on line coverage, 20% on assertions, 20% on gap penalty
            score = (
                (line_coverage_pct / 100) * 6
                + min(avg_assertions, 3) / 3 * 2
                + max(0.0, 1.0 - len(critical_gaps) * 0.1) * 2
            )
        else:
            # Fallback to file-ratio heuristic, capped at 7.0 (no report = penalised)
            score = (
                test_file_ratio * 3.5
                + min(avg_assertions, 3) / 3 * 2
                + max(0.0, 1.0 - len(critical_gaps) * 0.1) * 1.5
            )
        score = round(max(0.0, min(10.0, score)), 2)

        self.emit(
            queue,
            "progress",
            f"Test coverage: {test_count_files} test files, {source_count} source files, "
            f"{len(critical_gaps)} critical gaps, score={score}",
        )

        # 7. LLM analysis — send test files + their source counterparts (up to 6 pairs)
        llm_result = await self._llm_analysis(test_files, source_files, tested_sources, queue)
        missing_tests = llm_result.get("missing_tests", [])

        # Build findings list
        findings: List[Dict] = []
        for gap in critical_gaps:
            findings.append({
                "type": "error",
                "area": "Testing",
                "detail": f"Critical source file has no corresponding test: {gap}",
                "file": gap,
                "fix_hint": "Add unit and integration tests for this critical path",
            })
        for mt in missing_tests:
            if isinstance(mt, dict):
                findings.append({
                    "type": "suggestion",
                    "area": "Testing",
                    "detail": f"Missing test scenario: {mt.get('scenario', '')} in {mt.get('file', '')}",
                    "file": mt.get("file", ""),
                    "fix_hint": f"Add {mt.get('test_type', 'unit')} test for this scenario",
                })

        self.emit(queue, "result", data={"score": score})

        return {
            **state,
            "test_coverage": {
                "test_file_ratio": test_file_ratio,
                "test_count": test_count,
                "source_count": source_count,
                "critical_gaps": critical_gaps,
                "avg_assertions_per_test": avg_assertions,
                "has_mocks": has_mocks,
                "has_snapshots": has_snapshots,
                "missing_tests": missing_tests,
                "findings": findings,
                "testing_score": score,
                "line_coverage_pct": line_coverage_pct,
                "branch_coverage_pct": branch_coverage_pct,
                "coverage_source": coverage_source,
            },
        }

    def _parse_coverage_reports(self, temp_dir: str) -> Dict[str, Any]:
        """Search temp_dir for coverage reports and return parsed line/branch coverage."""
        if not temp_dir:
            return {"source": "none"}

        base = Path(temp_dir)
        result: Dict[str, Any] = {"source": "none"}

        # 1. coverage.xml (Python coverage XML — line-rate attribute on root element)
        for xml_path in base.rglob("coverage.xml"):
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                line_rate = root.get("line-rate")
                branch_rate = root.get("branch-rate")
                if line_rate is not None:
                    result["line_coverage_pct"] = round(float(line_rate) * 100, 1)
                if branch_rate is not None:
                    result["branch_coverage_pct"] = round(float(branch_rate) * 100, 1)
                result["source"] = "coverage.xml"
                return result
            except Exception:
                continue

        # 2. lcov.info (JS/TS lcov format — LF: lines found, LH: lines hit)
        for lcov_path in base.rglob("lcov.info"):
            try:
                lf_total, lh_total = 0, 0
                bf_total, bh_total = 0, 0
                for line in lcov_path.read_text(errors="ignore").splitlines():
                    if line.startswith("LF:"):
                        lf_total += int(line[3:].strip())
                    elif line.startswith("LH:"):
                        lh_total += int(line[3:].strip())
                    elif line.startswith("BRF:"):
                        bf_total += int(line[4:].strip())
                    elif line.startswith("BRH:"):
                        bh_total += int(line[4:].strip())
                if lf_total > 0:
                    result["line_coverage_pct"] = round(lh_total / lf_total * 100, 1)
                if bf_total > 0:
                    result["branch_coverage_pct"] = round(bh_total / bf_total * 100, 1)
                result["source"] = "lcov.info"
                return result
            except Exception:
                continue

        # 3. coverage-summary.json (Jest/Istanbul JSON summary)
        for json_path in base.rglob("coverage-summary.json"):
            try:
                data = json.loads(json_path.read_text(errors="ignore"))
                total = data.get("total", {})
                lines = total.get("lines", {})
                branches = total.get("branches", {})
                if "pct" in lines:
                    result["line_coverage_pct"] = round(float(lines["pct"]), 1)
                if "pct" in branches:
                    result["branch_coverage_pct"] = round(float(branches["pct"]), 1)
                if "line_coverage_pct" in result:
                    result["source"] = "coverage-summary.json"
                    return result
            except Exception:
                continue

        return result

    async def _llm_analysis(
        self,
        test_files: Dict[str, Any],
        source_files: Dict[str, Any],
        tested_sources: set,
        queue: asyncio.Queue,
    ) -> Dict:
        self.emit(queue, "progress", "Running LLM test quality analysis...")

        # Build up to 6 test+source pairs
        pairs: List[tuple] = []
        for tp, te in test_files.items():
            if len(pairs) >= 6:
                break
            pairs.append((tp, te, None, None))

        # Try to find matching source files for the pairs
        enhanced_pairs = []
        for tp, te, _, _ in pairs:
            bname = tp.split("/")[-1].lower()
            src_path = None
            src_entry = None
            for sp, se in source_files.items():
                if sp in tested_sources:
                    sbname = sp.split("/")[-1].lower()
                    # Simple name proximity check
                    if sbname[:6] in bname or bname[:6] in sbname:
                        src_path = sp
                        src_entry = se
                        break
            enhanced_pairs.append((tp, te, src_path, src_entry))

        file_sections = []
        total_chars = 0
        max_chars = 5000

        for tp, te, sp, se in enhanced_pairs:
            for path, entry in [(tp, te), (sp, se)]:
                if not path or not entry:
                    continue
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

        prompt = f"""Are these tests testing meaningful behavior or just implementation details? What critical test cases are missing? Return ONLY valid JSON: {{"quality_assessment": "string", "missing_tests": [{{"file": "string", "test_type": "unit|integration|e2e", "scenario": "string"}}], "test_quality_score": 0.0}}

{combined}"""

        try:
            response = await ollama_chat(prompt, timeout=180)
            if not response:
                return {}
            parsed = parse_llm_json(response, default=None)
            if not parsed or not isinstance(parsed, dict):
                return {}
            return self.validate_output(parsed, TestCoverageLLMOutput, queue)
        except Exception as e:
            self.emit(queue, "progress", f"LLM test coverage analysis failed: {e}")
            return {}
