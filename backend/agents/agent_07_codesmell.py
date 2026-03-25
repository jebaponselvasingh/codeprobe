import asyncio
import hashlib
import re
from typing import Any, Dict, List, Tuple
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json
from guardrails.schemas import CodeSmellLLMOutput


class CodeSmellAgent(AgentBase):
    agent_id = "codesmell"
    agent_name = "Code Smell Detector"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Running static code smell analysis...")

        frontend_files = state.get("frontend_files", {})
        backend_files = state.get("backend_files", {})
        all_files = {**frontend_files, **backend_files}

        if not all_files:
            self.emit(queue, "progress", "No source files found, skipping code smell detection")
            return {
                **state,
                "code_smells": {
                    "smells": [],
                    "smell_density": 0.0,
                    "findings": [],
                    "code_quality_score": 5.0,
                    "refactoring_suggestions": [],
                },
            }

        # --- Static analysis (no LLM) ---
        smells, file_smell_counts, total_lines = self._static_analysis(all_files)

        total_smells = len(smells)
        smell_density = total_smells / (total_lines / 100) if total_lines > 0 else 0.0
        code_quality_score = round(max(0.0, min(10.0, 10.0 - smell_density * 1.5)), 2)

        self.emit(
            queue,
            "progress",
            f"Static smell analysis complete: {total_smells} smells found across {total_lines} lines "
            f"(density={smell_density:.2f})",
        )

        # --- LLM analysis on top 5 smelliest files ---
        top_smelly = sorted(file_smell_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_smelly_paths = [p for p, _ in top_smelly]

        llm_context = self.get_llm_context(state)
        llm_findings, refactoring_suggestions = await self._llm_analysis(all_files, top_smelly_paths, queue, llm_context)

        self.emit(queue, "result", data={"score": code_quality_score})

        return {
            **state,
            "code_smells": {
                "smells": smells,
                "smell_density": round(smell_density, 3),
                "findings": llm_findings,
                "code_quality_score": code_quality_score,
                "refactoring_suggestions": refactoring_suggestions,
            },
        }

    def _static_analysis(self, all_files: Dict[str, Any]) -> Tuple[List[Dict], Dict[str, int], int]:
        smells = []
        file_smell_counts: Dict[str, int] = {}
        total_lines = 0

        # Collect normalized code blocks for duplicate detection (file -> list of block hashes)
        all_blocks: Dict[str, List[str]] = {}  # hash -> list of file paths

        is_test_file = re.compile(r"test|spec|__tests__", re.IGNORECASE)
        is_config_file = re.compile(r"\.(json|yaml|yml|toml|ini|env|config\.js)$", re.IGNORECASE)

        for file_path, entry in all_files.items():
            content = entry.get("content", "")
            if not content:
                continue

            lines = content.splitlines()
            file_line_count = len(lines)
            total_lines += file_line_count
            file_smells = 0

            is_react_file = file_path.endswith((".tsx", ".jsx"))
            is_py_file = file_path.endswith(".py")
            is_source = not is_test_file.search(file_path) and not is_config_file.search(file_path)

            # 1. God Component (React)
            if is_react_file:
                if file_line_count > 300:
                    smells.append({
                        "type": "god_component",
                        "file": file_path,
                        "detail": f"God component: {file_line_count} lines (>300)",
                        "severity": "high",
                    })
                    file_smells += 1
                use_state_count = len(re.findall(r"\buseState\s*\(", content))
                if use_state_count > 8:
                    smells.append({
                        "type": "god_component",
                        "file": file_path,
                        "detail": f"God component: {use_state_count} useState calls (>8)",
                        "severity": "medium",
                    })
                    file_smells += 1

            # 2. God Function — approximate by counting lines between def/function
            if is_py_file:
                func_bodies = self._get_python_function_bodies(lines)
                for func_name, start_line, length in func_bodies:
                    if length > 50:
                        smells.append({
                            "type": "god_function",
                            "file": file_path,
                            "line": start_line,
                            "detail": f"God function '{func_name}': {length} lines (>50)",
                            "severity": "medium",
                        })
                        file_smells += 1

            # 3. God File
            if file_line_count > 500:
                smells.append({
                    "type": "god_file",
                    "file": file_path,
                    "detail": f"God file: {file_line_count} lines (>500)",
                    "severity": "medium",
                })
                file_smells += 1

            # 4. Deep nesting (5+ levels of indentation)
            for i, line in enumerate(lines, start=1):
                stripped = line.lstrip()
                if not stripped:
                    continue
                indent = len(line) - len(stripped)
                # Check for tabs (each tab = 1 level) or spaces (4 spaces = 1 level)
                if "\t" in line[:indent]:
                    level = indent  # count tabs directly
                else:
                    level = indent // 4
                if level >= 5:
                    smells.append({
                        "type": "deep_nesting",
                        "file": file_path,
                        "line": i,
                        "detail": f"Deep nesting: {level} levels of indentation",
                        "severity": "low",
                    })
                    file_smells += 1
                    break  # Only report once per file to avoid noise

            # 5. Magic numbers (non-test, non-config source files)
            if is_source:
                magic_pattern = re.compile(r"\b(?!(?:0|1|-1|2|100)\b)\d{2,}\b")
                for i, line in enumerate(lines, start=1):
                    stripped = line.strip()
                    if stripped.startswith(("#", "//", "*")):
                        continue
                    # Skip line if it looks like a constant assignment
                    if re.match(r"[A-Z_]+\s*=\s*\d+", stripped):
                        continue
                    if magic_pattern.search(stripped):
                        smells.append({
                            "type": "magic_number",
                            "file": file_path,
                            "line": i,
                            "detail": f"Magic number in logic",
                            "severity": "low",
                        })
                        file_smells += 1
                        break  # One per file to reduce noise

            # 6. Long parameter lists
            if is_py_file:
                for i, line in enumerate(lines, start=1):
                    m = re.search(r"def\s+\w+\s*\(([^)]+)\)", line)
                    if m:
                        params = m.group(1)
                        # Count commas, ignoring *args/**kwargs defaults
                        param_count = len([p for p in params.split(",") if p.strip() and p.strip() not in ("", "*")])
                        if param_count > 5:
                            smells.append({
                                "type": "long_parameter_list",
                                "file": file_path,
                                "line": i,
                                "detail": f"Function with {param_count} parameters (>5)",
                                "severity": "low",
                            })
                            file_smells += 1

            # 7. Empty catch blocks
            for i, line in enumerate(lines, start=1):
                if re.search(r"except.*:\s*$", line) and i < len(lines):
                    next_line = lines[i].strip() if i < len(lines) else ""
                    if next_line == "pass" or next_line == "":
                        smells.append({
                            "type": "empty_catch",
                            "file": file_path,
                            "line": i,
                            "detail": "Empty except block (silently swallowing exceptions)",
                            "severity": "medium",
                        })
                        file_smells += 1
                # JS/TS empty catch
                if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", line):
                    smells.append({
                        "type": "empty_catch",
                        "file": file_path,
                        "line": i,
                        "detail": "Empty catch block",
                        "severity": "medium",
                    })
                    file_smells += 1

            # 8. TODO/FIXME/HACK/XXX markers
            todo_count = len(re.findall(r"#\s*(TODO|FIXME|HACK|XXX)\b", content, re.IGNORECASE))
            # Also catch JS-style
            todo_count += len(re.findall(r"//\s*(TODO|FIXME|HACK|XXX)\b", content, re.IGNORECASE))
            if todo_count > 0:
                smells.append({
                    "type": "todo_marker",
                    "file": file_path,
                    "detail": f"{todo_count} TODO/FIXME/HACK markers found",
                    "severity": "low",
                })
                file_smells += todo_count

            # 9. Console pollution (JS/TS)
            if file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
                console_count = len(re.findall(r"\bconsole\.(log|warn|error)\s*\(", content))
                if console_count > 0:
                    smells.append({
                        "type": "console_pollution",
                        "file": file_path,
                        "detail": f"{console_count} console.log/warn/error calls",
                        "severity": "low",
                    })
                    file_smells += console_count

            # Collect 8-line code blocks for duplicate detection
            if is_source and file_line_count >= 8:
                normalized_lines = [l.strip() for l in lines if l.strip()]
                for block_start in range(len(normalized_lines) - 7):
                    block = "\n".join(normalized_lines[block_start:block_start + 8])
                    block_hash = hashlib.md5(block.encode()).hexdigest()
                    if block_hash not in all_blocks:
                        all_blocks[block_hash] = []
                    all_blocks[block_hash].append(file_path)

            file_smell_counts[file_path] = file_smells

        # 10. Duplicate code detection
        reported_dupes = set()
        for block_hash, file_list in all_blocks.items():
            unique_files = list(set(file_list))
            if len(unique_files) >= 2:
                pair_key = tuple(sorted(unique_files[:2]))
                if pair_key not in reported_dupes:
                    reported_dupes.add(pair_key)
                    smells.append({
                        "type": "duplicate_code",
                        "file": unique_files[0],
                        "detail": f"Duplicate code block found in: {', '.join(unique_files[:3])}",
                        "severity": "medium",
                    })
                    # Count as smell for both files
                    for fp in unique_files[:2]:
                        file_smell_counts[fp] = file_smell_counts.get(fp, 0) + 1

        return smells, file_smell_counts, total_lines

    def _get_python_function_bodies(self, lines: List[str]) -> List[Tuple[str, int, int]]:
        """Return (func_name, start_line, body_length) for each function definition."""
        results = []
        func_starts = []

        for i, line in enumerate(lines):
            m = re.match(r"^(\s*)(?:async\s+)?def\s+(\w+)\s*\(", line)
            if m:
                indent_len = len(m.group(1))
                func_name = m.group(2)
                func_starts.append((i, indent_len, func_name))

        for idx, (start_i, indent_len, func_name) in enumerate(func_starts):
            # Find end: next line with same or lesser indent that starts a def or class
            end_i = len(lines)
            for j in range(start_i + 1, len(lines)):
                line = lines[j]
                if not line.strip():
                    continue
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_len and line.strip():
                    end_i = j
                    break
            length = end_i - start_i
            results.append((func_name, start_i + 1, length))

        return results

    async def _llm_analysis(
        self, all_files: Dict[str, Any], top_smelly_paths: List[str], queue: asyncio.Queue, llm_context: str = ""
    ):
        self.emit(queue, "progress", "Running LLM analysis on smelliest files...")

        if not top_smelly_paths:
            return [], []

        # Build prompt content (truncate to ~5000 chars)
        file_sections = []
        total_chars = 0
        max_chars = 5000

        for path in top_smelly_paths:
            entry = all_files.get(path, {})
            content = entry.get("content", "")
            if not content:
                continue
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
            return [], []

        prompt = f"""{llm_context + chr(10) + chr(10) if llm_context else ""}Review these files for architectural smells, high coupling, missing abstractions, and refactoring opportunities.

{combined}

Return ONLY valid JSON:
{{
  "findings": [
    {{
      "type": "suggestion",
      "area": "architecture|coupling|abstraction|readability|maintainability",
      "detail": "description of the smell or issue",
      "file": "filename",
      "fix_hint": "how to refactor"
    }}
  ],
  "refactoring_suggestions": [
    {{
      "title": "Short title for the refactoring",
      "before": "code or pattern before refactoring",
      "after": "code or pattern after refactoring"
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

            validated = self.validate_output(parsed, CodeSmellLLMOutput, queue)
            findings = validated.get("findings", [])
            refactoring_suggestions = validated.get("refactoring_suggestions", [])
            return findings, refactoring_suggestions

        except Exception as e:
            self.emit(queue, "progress", f"LLM code smell analysis failed: {e}")
            return [], []
