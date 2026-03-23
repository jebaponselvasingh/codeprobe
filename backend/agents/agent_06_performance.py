import asyncio
import re
from typing import Any, Dict, List
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json


class PerformanceAgent(AgentBase):
    agent_id = "performance"
    agent_name = "Performance Profiler"
    phase = 2

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Running performance static analysis...")

        frontend_files = state.get("frontend_files", {})
        backend_files = state.get("backend_files", {})

        if not frontend_files and not backend_files:
            self.emit(queue, "progress", "No files found, skipping performance analysis")
            return {
                **state,
                "performance_profile": {
                    "frontend_issues": [],
                    "backend_issues": [],
                    "findings": [],
                    "performance_score": 5.0,
                },
            }

        frontend_issues = self._check_frontend(frontend_files)
        backend_issues = self._check_backend(backend_files)

        all_static_findings = frontend_issues + backend_issues

        self.emit(
            queue,
            "progress",
            f"Static performance checks: {len(frontend_issues)} frontend issues, "
            f"{len(backend_issues)} backend issues",
        )

        # LLM analysis — send 4 largest frontend + 4 largest backend files
        llm_context = self.get_llm_context(state)
        llm_findings = await self._llm_analysis(frontend_files, backend_files, queue, llm_context)

        all_findings = all_static_findings + llm_findings

        # Scoring: base 7.0, subtract by issue severity
        warning_count = sum(1 for f in all_findings if f.get("type") == "warning")
        suggestion_count = sum(1 for f in all_findings if f.get("type") == "suggestion")
        score = 7.0 - (warning_count * 0.5) - (suggestion_count * 0.25)
        score = round(max(0.0, min(10.0, score)), 2)

        self.emit(queue, "result", data={"score": score})

        return {
            **state,
            "performance_profile": {
                "frontend_issues": frontend_issues,
                "backend_issues": backend_issues,
                "findings": all_findings,
                "performance_score": score,
            },
        }

    def _check_frontend(self, frontend_files: Dict[str, Any]) -> List[Dict]:
        issues = []
        if not frontend_files:
            return issues

        all_content = "\n".join(
            entry.get("content", "") for entry in frontend_files.values()
        )

        # 1. Heavy imports: moment or lodash default import
        for file_path, entry in frontend_files.items():
            content = entry.get("content", "")
            if not content:
                continue
            if re.search(r"import\s+\w+\s+from\s+['\"]moment['\"]", content):
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": "Heavy import: moment.js detected (use date-fns or Temporal instead)",
                    "file": file_path,
                    "fix_hint": "Replace moment with date-fns or the native Intl API to reduce bundle size",
                })
            if re.search(r"import\s+_\s+from\s+['\"]lodash['\"]", content):
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": "Heavy import: lodash default import detected (use named imports)",
                    "file": file_path,
                    "fix_hint": "Use named imports like `import { debounce } from 'lodash'` or switch to lodash-es",
                })

        # 2. Re-render traps: inline objects/arrays in JSX props outside useMemo/useCallback
        for file_path, entry in frontend_files.items():
            content = entry.get("content", "")
            if not content:
                continue
            inline_obj = re.findall(r"={{", content)
            inline_arr = re.findall(r"={\[", content)
            if (len(inline_obj) + len(inline_arr)) > 2:
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": f"Possible re-render trap: {len(inline_obj)} inline objects and {len(inline_arr)} inline arrays in JSX props",
                    "file": file_path,
                    "fix_hint": "Wrap inline object/array props in useMemo or move them outside the component",
                })

        # 3. useEffect with missing deps array
        for file_path, entry in frontend_files.items():
            content = entry.get("content", "")
            if not content:
                continue
            use_effect_calls = re.findall(r"useEffect\s*\(", content)
            # Count those that have a deps array argument (second argument with [])
            deps_present = re.findall(r"useEffect\s*\([^)]*,\s*\[", content)
            missing = len(use_effect_calls) - len(deps_present)
            if missing > 0:
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": f"useEffect missing dependency array in {missing} occurrence(s)",
                    "file": file_path,
                    "fix_hint": "Add a dependency array as the second argument to useEffect to prevent infinite re-renders",
                })

        # 4. Large lists without virtualization
        map_counts: Dict[str, int] = {}
        for file_path, entry in frontend_files.items():
            content = entry.get("content", "")
            if not content:
                continue
            count = len(re.findall(r"\.map\(", content))
            if count > 0:
                map_counts[file_path] = count

        has_virtualization = bool(
            re.search(r"react-window|react-virtual", all_content)
        )
        total_maps = sum(map_counts.values())
        if total_maps > 3 and not has_virtualization:
            top_file = max(map_counts, key=map_counts.get) if map_counts else ""
            issues.append({
                "type": "suggestion",
                "area": "Performance",
                "detail": f"Large list rendering without virtualization: {total_maps} .map() calls found with no react-window/react-virtual",
                "file": top_file,
                "fix_hint": "Use react-window or @tanstack/virtual for long lists to avoid rendering thousands of DOM nodes",
            })

        # 5. Missing image lazy loading
        for file_path, entry in frontend_files.items():
            content = entry.get("content", "")
            if not content:
                continue
            img_tags = re.findall(r"<img\s[^>]*>", content)
            for tag in img_tags:
                if 'loading=' not in tag:
                    issues.append({
                        "type": "suggestion",
                        "area": "Performance",
                        "detail": "Image tag missing loading='lazy' attribute",
                        "file": file_path,
                        "fix_hint": "Add loading=\"lazy\" to <img> tags to defer off-screen image loading",
                    })
                    break  # one finding per file

        # 6. No code splitting
        has_code_splitting = bool(
            re.search(r"React\.lazy|(?<!\w)lazy\(", all_content)
        )
        if not has_code_splitting and frontend_files:
            issues.append({
                "type": "suggestion",
                "area": "Performance",
                "detail": "No code splitting detected (no React.lazy or lazy() calls found)",
                "file": "",
                "fix_hint": "Use React.lazy() and Suspense for route-level code splitting to reduce initial bundle size",
            })

        # 7. Inline JSX event handlers without useCallback
        for file_path, entry in frontend_files.items():
            content = entry.get("content", "")
            if not content:
                continue
            inline_handlers = re.findall(r'on\w+\s*=\s*\{?\s*\(\s*\)\s*=>', content)
            has_use_callback = bool(re.search(r"useCallback\s*\(", content))
            if len(inline_handlers) > 3 and not has_use_callback:
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": f"{len(inline_handlers)} inline arrow function handlers in JSX with no useCallback — creates new functions on every render",
                    "file": file_path,
                    "fix_hint": "Extract handlers to useCallback to keep referential stability and prevent unnecessary child re-renders",
                })

        # 8. N+1 API calls: fetch/axios inside .map() or forEach()
        for file_path, entry in frontend_files.items():
            content = entry.get("content", "")
            if not content:
                continue
            # Find .map( or forEach( blocks and check for fetch/axios inside them
            # Look for patterns where fetch or axios appears close after .map( or .forEach(
            if re.search(r"\.(map|forEach)\s*\([^)]*(?:fetch\s*\(|axios\.)", content, re.DOTALL):
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": "Potential N+1 API call: fetch/axios used inside .map() or .forEach()",
                    "file": file_path,
                    "fix_hint": "Batch API requests instead of calling them per-item; use Promise.all or a batch endpoint",
                })
            else:
                # Also check line-by-line proximity
                lines = content.splitlines()
                in_loop = False
                for line in lines:
                    if re.search(r"\.(map|forEach)\s*\(", line):
                        in_loop = True
                    elif in_loop and re.search(r"\bfetch\s*\(|axios\.", line):
                        issues.append({
                            "type": "suggestion",
                            "area": "Performance",
                            "detail": "Potential N+1 API call: fetch/axios used inside .map() or .forEach()",
                            "file": file_path,
                            "fix_hint": "Batch API requests instead of calling them per-item; use Promise.all or a batch endpoint",
                        })
                        in_loop = False
                        break
                    elif re.search(r"\)\s*;?\s*$", line) and in_loop:
                        in_loop = False

        return issues

    def _check_backend(self, backend_files: Dict[str, Any]) -> List[Dict]:
        issues = []
        if not backend_files:
            return issues

        all_content = "\n".join(
            entry.get("content", "") for entry in backend_files.values()
        )

        for file_path, entry in backend_files.items():
            content = entry.get("content", "")
            if not content or not file_path.endswith(".py"):
                continue

            lines = content.splitlines()

            # 1. Sync I/O in async handlers
            in_async = False
            for line in lines:
                if re.search(r"async def\s+\w+", line):
                    in_async = True
                elif in_async and re.search(r"^def\s+\w+", line):
                    in_async = False
                if in_async and re.search(r"\b(open|\.read|\.write)\s*\(", line):
                    if "aiofiles" not in content:
                        issues.append({
                            "type": "suggestion",
                            "area": "Performance",
                            "detail": "Synchronous I/O (open/read/write) inside async handler — blocks the event loop",
                            "file": file_path,
                            "fix_hint": "Use aiofiles for async file I/O inside async functions",
                        })
                        break

            # 2. N+1 queries: ORM query inside a for loop
            in_for = False
            for line in lines:
                stripped = line.strip()
                if re.match(r"for\s+\w+", stripped):
                    in_for = True
                elif in_for and re.search(r"(session|db)\.(query|execute)\s*\(", stripped):
                    issues.append({
                        "type": "suggestion",
                        "area": "Performance",
                        "detail": "N+1 query pattern: ORM query inside a for loop",
                        "file": file_path,
                        "fix_hint": "Use eager loading (joinedload/selectinload) or batch queries outside the loop",
                    })
                    in_for = False
                    break
                elif stripped and not stripped.startswith("#") and not stripped.startswith(" ") and not stripped.startswith("\t"):
                    in_for = False

            # 3. Missing pagination: SELECT * or .all() without .limit() or LIMIT
            if re.search(r"SELECT\s+\*|\.all\s*\(\s*\)", content):
                if not re.search(r"\.limit\s*\(|LIMIT\s+\d+", content):
                    issues.append({
                        "type": "suggestion",
                        "area": "Performance",
                        "detail": "Unbounded query: SELECT * or .all() without .limit() or LIMIT clause",
                        "file": file_path,
                        "fix_hint": "Add pagination with .limit() and .offset(), or use a FastAPI pagination library",
                    })

            # 4. No caching
            has_caching = bool(
                re.search(r"\bredis\b|cache|lru_cache|@cache", content, re.IGNORECASE)
            )
            if not has_caching:
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": "No caching detected in this backend file",
                    "file": file_path,
                    "fix_hint": "Consider adding Redis, functools.lru_cache, or FastAPI-cache for frequently accessed data",
                })

            # 5. Large file reads without streaming
            if re.search(r"open\s*\(.*\)\s*\.read\s*\(\s*\)", content):
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": "File read without size check or streaming (open(...).read())",
                    "file": file_path,
                    "fix_hint": "Use streaming reads or check file size before loading into memory",
                })

            # 6. iterrows() — pandas anti-pattern
            if re.search(r"\.iterrows\s*\(\s*\)", content):
                issues.append({
                    "type": "warning",
                    "area": "Performance",
                    "detail": "pandas.iterrows() detected — row-by-row iteration is very slow",
                    "file": file_path,
                    "fix_hint": "Use vectorized operations (.apply(), .where(), numpy operations) instead of iterrows()",
                })

            # 7. time.sleep() inside async function — blocks event loop
            if re.search(r"async def", content) and re.search(r"\btime\.sleep\s*\(", content):
                issues.append({
                    "type": "warning",
                    "area": "Performance",
                    "detail": "time.sleep() used inside async function — blocks the event loop",
                    "file": file_path,
                    "fix_hint": "Replace time.sleep() with await asyncio.sleep() inside async functions",
                })

        # 8. Big-O complexity: nested loops
        issues.extend(self._check_complexity_patterns(backend_files))

        return issues

    def _check_complexity_patterns(self, files: Dict[str, Any]) -> List[Dict]:
        """Detect O(n²) and O(n³) loop nesting, recursive-without-memoization, and string concat in loops."""
        issues = []
        for file_path, entry in files.items():
            content = entry.get("content", "")
            if not content or not file_path.endswith(".py"):
                continue

            lines = content.splitlines()
            # Track indentation-based nesting depth of for/while loops
            loop_indent_stack: List[int] = []
            max_depth_seen = 0

            for line in lines:
                stripped = line.lstrip()
                if not stripped or stripped.startswith("#"):
                    continue
                indent = len(line) - len(stripped)

                # Pop loops that are no longer in scope
                while loop_indent_stack and loop_indent_stack[-1] >= indent:
                    loop_indent_stack.pop()

                if re.match(r"(for|while)\s+", stripped):
                    loop_indent_stack.append(indent)
                    depth = len(loop_indent_stack)
                    if depth > max_depth_seen:
                        max_depth_seen = depth

            if max_depth_seen >= 3:
                issues.append({
                    "type": "warning",
                    "area": "Performance",
                    "detail": f"O(n³) complexity: triple-nested loop detected (nesting depth {max_depth_seen})",
                    "file": file_path,
                    "fix_hint": "Reduce nesting with early returns, hash maps, or algorithmic improvements",
                })
            elif max_depth_seen == 2:
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": "O(n²) complexity: double-nested loop detected",
                    "file": file_path,
                    "fix_hint": "Consider using a dict/set for O(1) lookups instead of inner loops",
                })

            # Recursive function without memoization
            func_names = re.findall(r"^\s*def\s+(\w+)\s*\(", content, re.MULTILINE)
            for fn in func_names:
                # Check if function calls itself
                fn_body_match = re.search(
                    r"def\s+" + re.escape(fn) + r"\s*\([^)]*\).*?(?=\ndef\s|\Z)",
                    content, re.DOTALL
                )
                if fn_body_match:
                    body = fn_body_match.group(0)
                    if re.search(r"\b" + re.escape(fn) + r"\s*\(", body):
                        # Check for memoization decorator in the 3 lines before def
                        pos = fn_body_match.start()
                        preceding = content[max(0, pos - 200):pos]
                        if not re.search(r"@(lru_cache|cache|functools\.lru_cache|functools\.cache)", preceding):
                            issues.append({
                                "type": "suggestion",
                                "area": "Performance",
                                "detail": f"Recursive function '{fn}' without memoization — may recompute overlapping subproblems",
                                "file": file_path,
                                "fix_hint": "Add @functools.lru_cache or @functools.cache decorator to cache results",
                            })
                            break  # one finding per file

            # String concatenation in a loop
            str_concat_in_loop = re.search(
                r"for\s+.+:\s*\n(?:[ \t]+[^\n]*\n)*?[ \t]+\w+\s*\+=\s*['\"]",
                content, re.MULTILINE
            )
            if str_concat_in_loop:
                issues.append({
                    "type": "suggestion",
                    "area": "Performance",
                    "detail": "String concatenation (+=) inside a loop creates O(n²) string copies",
                    "file": file_path,
                    "fix_hint": "Collect strings in a list and use ''.join(parts) after the loop",
                })

        return issues

    async def _llm_analysis(
        self,
        frontend_files: Dict[str, Any],
        backend_files: Dict[str, Any],
        queue: asyncio.Queue,
        llm_context: str = "",
    ) -> List[Dict]:
        self.emit(queue, "progress", "Running LLM performance analysis...")

        def top_n_by_size(files: Dict[str, Any], n: int) -> Dict[str, Any]:
            sorted_items = sorted(files.items(), key=lambda x: x[1].get("size", 0), reverse=True)
            return dict(sorted_items[:n])

        selected_fe = top_n_by_size(frontend_files, 4)
        selected_be = top_n_by_size(backend_files, 4)
        selected = {**selected_fe, **selected_be}

        if not selected:
            return []

        file_sections = []
        total_chars = 0
        max_chars = 6000

        for path, entry in selected.items():
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
            return []

        context_prefix = llm_context + "\n\n" if llm_context else ""
        prompt = f"""{context_prefix}Review these files for performance issues: bundle size impact, unnecessary re-renders, N+1 queries, blocking I/O, missing caching. Return ONLY valid JSON: {{"findings": [{{"type": "suggestion", "area": "Performance", "detail": "string", "file": "string", "fix_hint": "string"}}], "frontend_score": 0.0, "backend_score": 0.0}}

{combined}"""

        try:
            response = await ollama_chat(prompt, timeout=180)
            if not response:
                return []
            parsed = parse_llm_json(response, default=None)
            if not parsed or not isinstance(parsed, dict):
                return []
            findings = parsed.get("findings", [])
            return [f for f in findings if isinstance(f, dict)]
        except Exception as e:
            self.emit(queue, "progress", f"LLM performance analysis failed: {e}")
            return []
