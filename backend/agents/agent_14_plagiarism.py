import ast
import asyncio
import hashlib
import os
import re
import tokenize
import io
from typing import Any, Dict, List, Optional
from .base import AgentBase
from utils.ollama import ollama_chat, parse_llm_json

BOILERPLATE_FILES = {
    "App.tsx": ["import React", "function App()", "export default App"],
    "App.css": ["#root", ".App-logo", ".App-header"],
    "index.tsx": ["ReactDOM.createRoot", "document.getElementById('root')"],
    "reportWebVitals": [],  # entire file is boilerplate
    "setupTests": [],
    "vite-env.d.ts": ["/// <reference types"],
    "main.tsx": ["ReactDOM.createRoot", "StrictMode"],
}

FASTAPI_TUTORIAL_PATTERNS = [
    r"fake_items_db",
    r"class Item\(",
    r"items: dict\s*=\s*\{\}",
    r"/items/\{item_id\}",
    r"fastapi\.readthedocs",
]

TUTORIAL_VARIABLE_NAMES = [
    "todos", "todo_list", "fake_db", "posts", "fakePosts",
    "testUser", "dummy_data", "placeholder",
]

PLACEHOLDER_URLS = [
    "jsonplaceholder.typicode.com",
    "example.com",
    "httpbin.org",
    "reqres.in",
]


class PlagiarismAgent(AgentBase):
    agent_id = "plagiarism"
    agent_name = "Plagiarism Detector"
    phase = 3

    async def run(self, state: Dict[str, Any], queue: asyncio.Queue) -> Dict[str, Any]:
        self.emit(queue, "progress", "Starting originality and plagiarism analysis...")

        frontend_files: Dict[str, Any] = state.get("frontend_files", {}) or {}
        backend_files: Dict[str, Any] = state.get("backend_files", {}) or {}
        all_files = {**frontend_files, **backend_files}

        # Step 1 — Boilerplate fingerprinting (static)
        self.emit(queue, "progress", "Step 1/4: Fingerprinting boilerplate files...")
        total_files = len(all_files)
        boilerplate_count = 0
        boilerplate_detected: List[str] = []
        tutorial_signals: List[str] = []

        for path, entry in all_files.items():
            content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
            basename = os.path.basename(path)
            # Strip extension for matching
            basename_no_ext = os.path.splitext(basename)[0]

            # Check BOILERPLATE_FILES by basename or basename without extension
            matched_key = None
            for key in BOILERPLATE_FILES:
                if basename == key or basename_no_ext == key or basename.startswith(key):
                    matched_key = key
                    break

            if matched_key is not None:
                patterns = BOILERPLATE_FILES[matched_key]
                if len(patterns) == 0:
                    # Entire file is boilerplate
                    boilerplate_count += 1
                    boilerplate_detected.append(path)
                else:
                    match_count = sum(1 for p in patterns if p in content)
                    if match_count >= 2:
                        boilerplate_count += 1
                        boilerplate_detected.append(path)

        # Check FastAPI tutorial patterns in backend files
        for path, entry in backend_files.items():
            content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
            for pattern in FASTAPI_TUTORIAL_PATTERNS:
                if re.search(pattern, content):
                    signal = f"FastAPI tutorial pattern '{pattern}' in {path}"
                    if signal not in tutorial_signals:
                        tutorial_signals.append(signal)

        # Check tutorial variable names in all files
        for path, entry in all_files.items():
            content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
            for var_name in TUTORIAL_VARIABLE_NAMES:
                if var_name in content:
                    signal = f"Tutorial variable '{var_name}' in {path}"
                    if signal not in tutorial_signals:
                        tutorial_signals.append(signal)

        # Check placeholder URLs in all files
        for path, entry in all_files.items():
            content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
            for url in PLACEHOLDER_URLS:
                if url in content:
                    signal = f"Placeholder URL '{url}' in {path}"
                    if signal not in tutorial_signals:
                        tutorial_signals.append(signal)

        # Step 1b — AST fingerprinting and cross-submission similarity
        session_id = state.get("session_id", "")
        db_path = state.get("db_path", "")
        cross_matches: List[str] = []
        if session_id and db_path:
            self.emit(queue, "progress", "Step 1b: AST fingerprinting for cross-submission similarity...")
            fingerprints = self._compute_fingerprints(all_files)
            cross_matches = await self._check_cross_submission(fingerprints, session_id, db_path)
            if cross_matches:
                for match in cross_matches[:3]:
                    findings_prebuild = {"type": "warning", "area": "plagiarism", "detail": match, "file": ""}
                    tutorial_signals.append(match)

        # Step 2 — Custom code percentage
        self.emit(queue, "progress", "Step 2/4: Computing custom code ratio...")
        custom_file_count = total_files - boilerplate_count
        custom_ratio = custom_file_count / max(1, total_files)

        # Step 3 — Tutorial signal count
        self.emit(queue, "progress", "Step 3/4: Counting tutorial signals...")
        static_estimate = custom_ratio * 100

        # Step 4 — LLM Analysis
        self.emit(queue, "progress", "Step 4/4: Running LLM originality analysis...")
        llm_result = await self._llm_analysis(frontend_files, backend_files, queue)

        # Scoring
        llm_estimate = llm_result.get("originality_estimate", static_estimate)
        blended = static_estimate * 0.4 + llm_estimate * 0.6
        penalty = min(30, len(tutorial_signals) * 5)
        final_estimate = max(0, blended - penalty)
        originality_score = round(final_estimate / 10, 2)  # 0-10

        original_elements = llm_result.get("original_elements", [])
        llm_signals = llm_result.get("tutorial_signals", [])
        # Merge LLM-detected signals
        for sig in llm_signals:
            if sig not in tutorial_signals:
                tutorial_signals.append(sig)

        assessment = llm_result.get(
            "assessment",
            f"Static analysis found {boilerplate_count}/{total_files} boilerplate files and {len(tutorial_signals)} tutorial signals."
        )

        # Build findings
        findings: List[Dict] = []
        if boilerplate_count > 0:
            pct = round(boilerplate_count / max(1, total_files) * 100, 1)
            findings.append({
                "type": "info",
                "message": f"{boilerplate_count} boilerplate file(s) detected ({pct}% of total files): {', '.join(os.path.basename(p) for p in boilerplate_detected[:5])}",
            })
        if tutorial_signals:
            findings.append({
                "type": "warning",
                "message": f"{len(tutorial_signals)} tutorial/placeholder signal(s) detected. Review for originality.",
            })
        if originality_score < 4.0:
            findings.append({
                "type": "warning",
                "message": f"Low originality score ({originality_score}/10) — significant tutorial or boilerplate code detected.",
            })
        elif originality_score >= 7.0:
            findings.append({
                "type": "info",
                "message": f"Good originality score ({originality_score}/10) — project appears largely original.",
            })

        boilerplate_percentage = round((boilerplate_count / max(1, total_files)) * 100, 2)

        originality_report = {
            "originality_estimate": round(final_estimate, 2),
            "originality_score": originality_score,
            "boilerplate_percentage": boilerplate_percentage,
            "custom_ratio": round(custom_ratio, 4),
            "tutorial_signals": tutorial_signals,
            "original_elements": original_elements,
            "assessment": assessment,
            "cross_submission_matches": cross_matches,
            "findings": findings,
        }

        self.emit(queue, "result", data={"originality_score": originality_score})
        self.emit(queue, "progress", f"Originality analysis complete: {originality_score}/10")

        return {**state, "originality_report": originality_report}

    async def _llm_analysis(
        self,
        frontend_files: Dict[str, Any],
        backend_files: Dict[str, Any],
        queue: asyncio.Queue,
    ) -> Dict:
        """Send top files to LLM for originality assessment."""
        # Select top 5 largest non-boilerplate frontend files
        def file_size(item):
            path, entry = item
            content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
            return len(content)

        def is_boilerplate(path):
            basename = os.path.basename(path)
            basename_no_ext = os.path.splitext(basename)[0]
            for key in BOILERPLATE_FILES:
                if basename == key or basename_no_ext == key or basename.startswith(key):
                    return True
            return False

        fe_non_boilerplate = [
            (path, entry) for path, entry in frontend_files.items()
            if not is_boilerplate(path)
        ]
        fe_non_boilerplate.sort(key=file_size, reverse=True)
        top_fe = fe_non_boilerplate[:5]

        be_items = list(backend_files.items())
        be_items.sort(key=file_size, reverse=True)
        top_be = be_items[:3]

        file_excerpts_parts = []
        for path, entry in top_fe + top_be:
            content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
            excerpt = content[:1500]
            file_excerpts_parts.append(f"=== {path} ===\n{excerpt}")

        file_excerpts = "\n\n".join(file_excerpts_parts)

        if not file_excerpts.strip():
            return {}

        prompt = f"""Review these code files from a student project submission.

Files:
{file_excerpts}

Assess:
1. Does this appear to be mostly original student work or copy-pasted tutorials?
2. What percentage appears original (estimate 0-100)?
3. What tutorial patterns or boilerplate do you see?
4. What signs of genuine effort or original implementation exist?

Return JSON:
{{
  "originality_estimate": <0-100 integer>,
  "assessment": "<2-3 sentence summary>",
  "tutorial_signals": ["<signal1>"],
  "original_elements": ["<element1>"]
}}"""

        try:
            response = await ollama_chat(prompt, timeout=180)
            parsed = parse_llm_json(response, default=None)
            if parsed and isinstance(parsed, dict):
                return parsed
        except Exception as e:
            self.emit(queue, "progress", f"LLM originality analysis failed: {e}")

        return {}

    def _compute_fingerprints(self, all_files: Dict[str, Any]) -> Dict[str, str]:
        """Compute structural fingerprints for Python (.py) and JS/TS (.ts/.tsx/.js/.jsx) files."""
        fingerprints: Dict[str, str] = {}
        for file_path, entry in all_files.items():
            content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
            if not content:
                continue
            try:
                if file_path.endswith(".py"):
                    # AST-based: sequence of node type names
                    tree = ast.parse(content)
                    node_types = [type(node).__name__ for node in ast.walk(tree)]
                    fingerprint = hashlib.md5(",".join(node_types).encode()).hexdigest()
                elif re.search(r"\.(ts|tsx|js|jsx)$", file_path):
                    # Token-bag: extract identifiers and structural keywords
                    tokens = re.findall(
                        r"\b(function|class|const|let|var|if|for|while|return|import|export|async|await)\b|\b[A-Za-z_]\w{3,}\b",
                        content
                    )
                    token_str = ",".join(sorted(set(tokens)))
                    fingerprint = hashlib.md5(token_str.encode()).hexdigest()
                else:
                    continue
                basename = os.path.basename(file_path)
                fingerprints[basename] = fingerprint
            except Exception:
                continue
        return fingerprints

    async def _check_cross_submission(
        self, fingerprints: Dict[str, str], session_id: str, db_path: str
    ) -> List[str]:
        """Store fingerprints and compare against prior submissions. Returns match descriptions."""
        if not fingerprints or not db_path:
            return []
        matches: List[str] = []
        try:
            import aiosqlite
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                for file_path, fingerprint in fingerprints.items():
                    # Check for matching fingerprint from a different session
                    cursor = await db.execute(
                        "SELECT session_id FROM submission_fingerprints WHERE fingerprint=? AND session_id!=? LIMIT 1",
                        (fingerprint, session_id)
                    )
                    row = await cursor.fetchone()
                    if row:
                        matches.append(
                            f"File '{file_path}' has identical structure to submission {row['session_id'][:8]}..."
                        )
                # Store current submission's fingerprints
                for file_path, fingerprint in fingerprints.items():
                    await db.execute(
                        "INSERT OR REPLACE INTO submission_fingerprints (session_id, file_path, fingerprint) VALUES (?,?,?)",
                        (session_id, file_path, fingerprint)
                    )
                await db.commit()
        except Exception:
            pass
        return matches
