import ast
import asyncio
import re
from typing import Any, Dict, List
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json


def cyclomatic_complexity(tree) -> int:
    """Count branches: if, elif, for, while, and, or, except, with, assert, comprehension."""
    count = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                              ast.With, ast.Assert, ast.comprehension)):
            count += 1
        elif isinstance(node, ast.BoolOp):
            count += len(node.values) - 1
    return count


def get_function_complexity(source: str) -> list:
    """Return list of {name, complexity, line, lines} for each function/method."""
    results = []
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_tree = ast.parse(ast.unparse(node))
                cc = cyclomatic_complexity(func_tree)
                results.append({
                    "name": node.name,
                    "complexity": cc,
                    "line": node.lineno,
                    "lines": (node.end_lineno or node.lineno) - node.lineno + 1,
                })
    except Exception:
        pass
    return results


def ts_cyclomatic(content: str) -> int:
    """Count branch keywords as approximation for TypeScript/JavaScript."""
    keywords = ["if ", "else if", "for ", "while ", "catch ", "case ", "&&", "||", "?"]
    return 1 + sum(content.count(k) for k in keywords)


class ComplexityAgent(AgentBase):
    agent_id = "complexity"
    agent_name = "Complexity Analyzer"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Running complexity analysis on source files...")

        frontend_files = state.get("frontend_files", {})
        backend_files = state.get("backend_files", {})
        all_files = {**frontend_files, **backend_files}

        if not all_files:
            self.emit(queue, "progress", "No source files found, skipping complexity analysis")
            return {
                **state,
                "complexity_report": {
                    "avg_cyclomatic": 0.0,
                    "distribution": {"low": 0, "moderate": 0, "high": 0, "danger": 0},
                    "danger_functions": [],
                    "maintainability_index": 5.0,
                    "findings": [],
                    "refactoring_suggestions": [],
                    "complexity_score": 5.0,
                },
            }

        # --- Process all source files ---
        all_function_metrics: List[Dict] = []

        for file_path, entry in all_files.items():
            content = entry.get("content", "")
            if not content:
                continue

            if file_path.endswith(".py"):
                func_metrics = get_function_complexity(content)
                for m in func_metrics:
                    all_function_metrics.append({
                        "file": file_path,
                        "name": m["name"],
                        "complexity": m["complexity"],
                        "line": m["line"],
                        "lines": m["lines"],
                    })
            elif file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
                # File-level approximation for TS/JS
                cc = ts_cyclomatic(content)
                file_name = file_path.split("/")[-1]
                all_function_metrics.append({
                    "file": file_path,
                    "name": f"<{file_name}>",
                    "complexity": cc,
                    "line": 1,
                    "lines": len(content.splitlines()),
                })

        if not all_function_metrics:
            self.emit(queue, "progress", "No functions/files analyzed")
            return {
                **state,
                "complexity_report": {
                    "avg_cyclomatic": 0.0,
                    "distribution": {"low": 0, "moderate": 0, "high": 0, "danger": 0},
                    "danger_functions": [],
                    "maintainability_index": 5.0,
                    "findings": [],
                    "refactoring_suggestions": [],
                    "complexity_score": 5.0,
                },
            }

        # --- Aggregate metrics ---
        complexities = [m["complexity"] for m in all_function_metrics]
        avg_cyclomatic = round(sum(complexities) / len(complexities), 2)

        distribution = {"low": 0, "moderate": 0, "high": 0, "danger": 0}
        for cc in complexities:
            if cc <= 5:
                distribution["low"] += 1
            elif cc <= 10:
                distribution["moderate"] += 1
            elif cc <= 15:
                distribution["high"] += 1
            else:
                distribution["danger"] += 1

        # Top 10 most complex
        danger_functions = sorted(all_function_metrics, key=lambda x: x["complexity"], reverse=True)[:10]

        # Maintainability index (0-10)
        if avg_cyclomatic > 5:
            maintainability_index = max(0.0, min(10.0, 10.0 - (avg_cyclomatic - 5) * 0.5))
        else:
            maintainability_index = 8.0
        maintainability_index = round(maintainability_index, 2)

        complexity_score = maintainability_index

        self.emit(
            queue,
            "progress",
            f"Complexity analysis complete: avg={avg_cyclomatic:.1f}, "
            f"danger={distribution['danger']} functions, score={complexity_score}",
        )

        # --- LLM analysis on top 5 most complex functions ---
        llm_findings, refactoring_suggestions = await self._llm_analysis(
            all_files, danger_functions[:5], queue
        )

        self.emit(queue, "result", data={"score": complexity_score})

        return {
            **state,
            "complexity_report": {
                "avg_cyclomatic": avg_cyclomatic,
                "distribution": distribution,
                "danger_functions": danger_functions,
                "maintainability_index": maintainability_index,
                "findings": llm_findings,
                "refactoring_suggestions": refactoring_suggestions,
                "complexity_score": complexity_score,
            },
        }

    async def _llm_analysis(
        self, all_files: Dict[str, Any], top_functions: List[Dict], queue: asyncio.Queue
    ):
        self.emit(queue, "progress", "Running LLM analysis on most complex functions...")

        if not top_functions:
            return [], []

        # Build context: extract function source snippets
        func_sections = []
        total_chars = 0
        max_chars = 5000

        for func_info in top_functions:
            file_path = func_info.get("file", "")
            func_name = func_info.get("name", "unknown")
            func_line = func_info.get("line", 1)
            func_lines = func_info.get("lines", 20)
            complexity = func_info.get("complexity", 0)

            entry = all_files.get(file_path, {})
            content = entry.get("content", "")
            if not content:
                continue

            lines = content.splitlines()
            start = max(0, func_line - 1)
            end = min(len(lines), start + func_lines + 5)
            snippet = "\n".join(lines[start:end])

            header = (
                f"\n--- {file_path}:{func_line} | function: {func_name} | "
                f"cyclomatic complexity: {complexity} ---\n"
            )
            available = max_chars - total_chars - len(header) - 100
            if available <= 0:
                break

            section = header + snippet[:available]
            func_sections.append(section)
            total_chars += len(section)
            if total_chars >= max_chars:
                break

        combined = "".join(func_sections)
        if not combined.strip():
            return [], []

        prompt = f"""These are the most complex functions in the codebase. For each, suggest a refactoring approach to reduce complexity.

{combined}

Return ONLY valid JSON:
{{
  "suggestions": [
    {{
      "function_name": "name of the function",
      "file": "file path",
      "current_complexity": 0,
      "approach": "description of the refactoring approach",
      "pseudocode": "simplified pseudocode showing the refactored structure"
    }}
  ]
}}"""

        try:
            response = await ollama_chat(prompt, timeout=180)
            if not response:
                return [], []

            parsed = parse_llm_json(response, default=None)
            if not parsed or not isinstance(parsed, dict):
                return [], []

            suggestions = parsed.get("suggestions", [])

            # Convert suggestions to findings format for consistency
            findings = []
            for s in suggestions:
                findings.append({
                    "type": "suggestion",
                    "area": "complexity",
                    "detail": f"High complexity in '{s.get('function_name', '')}' (CC={s.get('current_complexity', '?')}): {s.get('approach', '')}",
                    "file": s.get("file", ""),
                    "fix_hint": s.get("pseudocode", ""),
                })

            return findings, suggestions

        except Exception as e:
            self.emit(queue, "progress", f"LLM complexity analysis failed: {e}")
            return [], []
