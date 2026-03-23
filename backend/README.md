# CodeProbe Backend

FastAPI + aiosqlite + Ollama — 100% local, no cloud dependencies.

## Quick Start

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.ai) running locally

```bash
ollama pull qwen2.5:14b
ollama serve
```

### Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
python main.py
# or
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Run Tests

```bash
pytest tests/ -v
```

---

## Architecture

```
main.py              FastAPI app + CORS + lifespan
database.py          SQLite schema + seed data
pipeline.py          16-agent orchestration (asyncio.gather)
agents/
  agent_01_extract   ZIP extraction + file classification
  agent_02_structure Framework detection (React/FastAPI/etc.)
  agent_03_react     React best practices analysis
  agent_04_fastapi   FastAPI patterns analysis
  agent_05_security  OWASP security checks
  agent_06_perf      Performance profiling
  agent_07_codesmell Code smell detection
  agent_08_testcov   Test coverage analysis
  agent_09_deps      Dependency audit
  agent_10_access    WCAG accessibility checks
  agent_11_docs      Documentation scoring
  agent_12_integ     Frontend/backend integration analysis
  agent_13_req       Requirements validation
  agent_14_plagiarism Originality + AST similarity detection
  agent_15_complex   Cyclomatic complexity analysis
  agent_16_report    Final report generation + critic pass
api/
  review.py          POST /review, SSE stream, fix-suggestion, file serving
  batch.py           Batch review + comparison
  history.py         History + progress endpoints
  profiles.py        Profile + rubric CRUD
  diagram.py         Architecture diagram generation
  health.py          Health check + Ollama status
utils/
  ollama.py          Ollama HTTP client + JSON parser
```

## Environment

No `.env` required. Ollama is expected at `http://localhost:11434`.
Override with `OLLAMA_BASE_URL` and `OLLAMA_MODEL` environment variables.

## Database

SQLite at `./data/reviews.db`. Created automatically on first run.

Tables:
- `reviews` — review sessions, scores, report JSON
- `profiles` — built-in and custom review profiles
- `rubrics` — custom scoring rubrics
- `chat_messages` — per-session AI chat history
- `batch_reviews` — batch review jobs
- `batch_members` — mapping of batch jobs to individual reviews
- `submission_fingerprints` — AST/token fingerprints for cross-submission plagiarism detection

---

## Improvements & Technical Details

This section documents all significant improvements made to the review pipeline, accuracy mechanisms, and feature completeness.

---

### 1. Fix Suggestion UI — SSE Payload Shape Fix

**Area:** `api/review.py` → `frontend/src/components/report/FindingDiffView.tsx`

**Problem:** The "Show Fix" button in every finding card was silently broken. The backend `/review/{session_id}/fix-suggestion` endpoint streams a Server-Sent Event with the shape:

```json
{ "type": "result", "original_code": "...", "fixed_code": "...", "explanation": "..." }
```

The frontend was parsing the event but then checking `event.data` — a field that does not exist in the payload. Because `event.data` was always `undefined`, `setResult()` was never called and the diff viewer never rendered.

**Fix:** Updated the TypeScript event type annotation to include `original_code`, `fixed_code`, and `explanation` as top-level optional fields. The result object is now constructed directly from these fields:

```typescript
setResult({
  original_code: event.original_code ?? '',
  fixed_code:    event.fixed_code   ?? '',
  explanation:   event.explanation  ?? '',
});
```

Additionally, `FindingCard.tsx` was using `String(Math.random())` as the `findingId` prop. Because this generated a new random ID on every render, the backend cache keyed on `finding_id` was never hit — every click triggered a fresh Ollama call even for the same finding. Fixed by using the stable `finding.id` from the report data.

---

### 2. Quick Mode — End-to-End Wiring

**Area:** `frontend/src/stores/reviewStore.ts` → `api/review.py` → `pipeline.py`

**Problem:** The Quick Mode toggle existed in the upload UI and was stored in Zustand state, but it was never appended to the `FormData` POST body. The backend had no parameter to receive it, and the pipeline had no logic to act on it.

**Fix — Frontend:** In `reviewStore.ts`, `startReview()` now reads `quickMode` from store state and conditionally appends it:

```typescript
if (quickMode) form.append('quick_mode', 'true');
```

**Fix — Backend API:** `review.py`'s `start_review()` endpoint now accepts:

```python
quick_mode: bool = Form(False)
```

This value is forwarded to `run_pipeline()` as a named argument.

**Fix — Pipeline:** `pipeline.py` defines a `quick_skip` list when `quick_mode=True`:

```python
quick_skip = ["plagiarism", "documentation", "accessibility", "requirements", "complexity"]
```

These are the five slowest, lowest-priority agents. The parallel agent filter checks both `skip_agents` (from profile) and `quick_skip`. Phase 3 agents (`RequirementsAgent`, `PlagiarismAgent`) are also individually guarded and skipped. The progress message includes `[quick mode]` so the user can see it in the stream.

**Effect:** Quick Mode reduces review time by approximately 40–60% by skipping the two Phase 3 LLM-heavy agents and three Phase 2 agents, while retaining all core analysis (security, React, FastAPI, code smell, performance, test coverage, dependencies).

---

### 3. Rubric Scoring — Applied to Actual Score Calculation

**Area:** `pipeline.py` → `agents/agent_16_report.py`

**Problem:** Rubrics were fully CRUD-able through the UI, stored in the `rubrics` DB table, and the `rubric_id` was persisted on each review — but `pipeline.py` never loaded the rubric from the database, and `agent_16_report.py` never referenced it when computing the weighted overall score. Rubrics were metadata only.

**Fix — Pipeline:** Added `_load_rubric_config()` helper that queries `SELECT name, categories_json FROM rubrics WHERE id=?` and returns a structured dict:

```python
{
  "id": "...",
  "name": "Custom Rubric Name",
  "categories": [
    { "name": "Code Quality", "weight": 0.4, "min_expectations": "..." },
    ...
  ]
}
```

This is stored in `state["rubric_config"]` and is available to all downstream agents.

**Fix — Report Agent:** The `_weight()` function now follows a three-tier priority:

1. **Rubric weights** — category name normalized to `snake_case` (e.g. `"Code Quality"` → `"code_quality"`) and looked up first
2. **Profile custom weights** — `profile_config["scoring_weights"]` from the selected profile
3. **System defaults** — `DEFAULT_WEIGHTS` hardcoded in the report agent

Rubric weights are also auto-normalized to sum to 1.0 if the user's categories don't add up exactly:

```python
if total > 0 and abs(total - 1.0) > 0.01:
    rubric_weights = {k: v / total for k, v in rubric_weights.items()}
```

**Fix — Executive Summary:** The LLM executive summary prompt now includes rubric `min_expectations` per category, so the LLM grades the student against the actual criteria defined in the rubric rather than generic guidelines. The report `meta` block also records which rubric was applied (`rubric` and `rubric_id` fields).

---

### 4. LLM Prompt Tuning — Strictness and Tone Injection

**Area:** `agents/base.py` → agents 03, 04, 05, 06, 07, 11

**Problem:** Every profile has `strictness` (lenient / moderate / strict / very_strict) and `llm_tone` (e.g. "encouraging and supportive", "formal and compliance-focused"). These values were loaded into `state["profile_config"]` but no LLM agent ever read them — every agent ran with identical prompt behaviour regardless of profile.

**Fix — Base Class:** Added `get_llm_context()` method to `AgentBase`:

```python
def get_llm_context(self, state: dict) -> str:
    profile = state.get("profile_config") or {}
    lines = [
        f"Review strictness: {profile.get('strictness', 'moderate')}.",
        f"Tone: {profile.get('llm_tone', 'constructive and direct')}.",
    ]
    # Also inject rubric expectations if a rubric is active
    cats = (state.get("rubric_config") or {}).get("categories", [])
    if cats:
        lines.append("Rubric requirements: " + "; ".join(
            f"{c['name']}: {c['min_expectations']}"
            for c in cats if c.get("min_expectations")
        ))
    return "\n".join(lines)
```

**Fix — Each Agent:** In each of the 6 LLM-calling agents, `run()` now calls `self.get_llm_context(state)` once and passes the result into `_llm_analysis()` as a `llm_context: str = ""` parameter. The context string is prepended to the prompt before the code content.

**Effect:** With the `beginner` profile, the LLM will phrase findings in an encouraging, non-intimidating way. With `enterprise` or `interview`, it will produce stricter, more formal output with higher expectations. When a rubric is active, every agent is aware of the grading criteria.

---

### 5. Test Coverage — Real Coverage Report Parsing

**Area:** `agents/agent_08_testcoverage.py`

**Problem:** Test coverage scoring was entirely based on counting test files and test functions via regex. A project that had 100% line coverage but no report file would score the same as a project with 5% coverage that happened to have many test files. There was no actual coverage measurement.

**Fix:** Added `_parse_coverage_reports(temp_dir)` that walks the session's extracted directory searching for three standard coverage formats:

**`coverage.xml`** (Python `coverage.py` with `--xml`):
```python
tree = ET.parse(xml_path)
line_rate = tree.getroot().get("line-rate")  # float 0.0–1.0
branch_rate = tree.getroot().get("branch-rate")
```

**`lcov.info`** (Jest, Vitest, Istanbul, nyc):
```
LF:180    # Lines Found
LH:162    # Lines Hit
BRF:44    # Branches Found
BRH:38    # Branches Hit
```
Coverage = `sum(LH) / sum(LF) * 100` across all source files.

**`coverage-summary.json`** (Jest JSON reporter):
```json
{ "total": { "lines": { "pct": 89.7 }, "branches": { "pct": 72.1 } } }
```

**Scoring Impact:** When a coverage report is found, the score formula changes from a file-ratio heuristic to an actual coverage-weighted formula:

```
score = (line_coverage_pct / 100) * 6   # 60% weight on real coverage
      + min(avg_assertions, 3) / 3 * 2   # 20% on assertion density
      + max(0, 1 - critical_gaps * 0.1) * 2  # 20% on untested critical paths
```

Without a coverage report, the fallback formula is capped at a maximum of 7.0 to penalise the absence of instrumentation. The `line_coverage_pct`, `branch_coverage_pct`, and `coverage_source` fields are included in the agent's output for display in the UI.

---

### 6. Performance Agent — Big-O and Static Pattern Enhancements

**Area:** `agents/agent_06_performance.py`

**Problem:** The performance agent detected some useful patterns (N+1 in frontend, sync I/O in async handlers) but had no concept of algorithmic complexity. It also missed several common React and Python performance anti-patterns.

**New: `_check_complexity_patterns(files)` method**

Analyses Python files for three complexity issues:

**Nested loop detection (O(n²) / O(n³)):**
Tracks loop indentation depth by maintaining a stack. When a `for` or `while` keyword is encountered, its indentation level is pushed onto the stack. Lines that dedent pop stale entries. Maximum nesting depth is computed per file:
- Depth ≥ 3 → `warning`: O(n³) complexity
- Depth = 2 → `suggestion`: O(n²) complexity

**Recursive functions without memoization:**
Extracts all `def func_name()` definitions, then checks if the function body contains a self-call via `\bfunc_name\s*\(`. If a self-call exists but no `@lru_cache` or `@cache` decorator appears in the 200 characters before the `def`, it flags the function with a suggestion to add `@functools.lru_cache`.

**String concatenation in loops:**
Detects the pattern `variable += "..."` inside a `for` block using a multi-line regex. String `+=` in a loop creates O(n²) memory copies because Python strings are immutable. The fix suggestion points to `''.join(parts)`.

**New frontend checks:**

**Inline JSX event handlers without `useCallback`:**
Counts all `onClick={() => ...}` / `onSubmit={() => ...}` style inline arrow functions. If a component defines more than 3 such handlers without any `useCallback` call, it flags it — each render creates new function objects, breaking referential equality for memoised child components.

**Backend additions:**

- `iterrows()` detection: Pandas row iteration is 10–100x slower than vectorized operations. Flagged as a `warning` with a suggestion to use `.apply()` or numpy operations.
- `time.sleep()` in async functions: Blocks the entire event loop thread. Detected when both `async def` and `time.sleep(` appear in the same file. Fix suggestion: `await asyncio.sleep()`.

**Scoring update:** Score now uses severity-weighted deduction (`warning * 0.5 + suggestion * 0.25`) rather than a flat per-issue count, so warnings from nested loops carry more weight than minor suggestions.

---

### 7. Multi-Pass LLM Critic Review

**Area:** `agents/agent_16_report.py`

**Problem:** All findings came from a single forward pass of static analysis and LLM agents. There was no mechanism to filter false positives — findings triggered on variable names, test fixture code, framework boilerplate, or commented-out examples were treated identically to real issues.

**Fix:** Added `_llm_critic_pass(findings, state, queue)` method, called after `_aggregate_findings()` but before scoring and report assembly.

**How it works:**

1. Takes the top 20 `error` and `warning` findings — the most impactful ones, which are also most likely to have false positives from stricter agents.

2. Serialises them as compact JSON with stable indices:
```json
[{"i": 0, "type": "error", "area": "security", "detail": "...", "file": "..."}, ...]
```
Truncated to 3000 characters to stay within a short LLM context window.

3. Sends a targeted critic prompt:
```
You are a senior code reviewer validating automated findings.
Review strictness: {strictness}.
Mark any clearly false positives (triggered by variable names, test code,
framework boilerplate) with false_positive=true.
Return ONLY valid JSON: [{"i": 0, "false_positive": false}, ...]
```

4. The LLM returns a parallel array of `{i, false_positive}` objects. Any finding where `false_positive: true` is tagged for removal using Python's `id()` to match original object references.

5. **Fallback safety:** If the LLM call fails, returns fewer than half the expected entries, or throws an exception, the original unfiltered findings list is returned unchanged. The critic pass can never remove all findings.

6. **Quick Mode:** Skipped entirely when `quick_mode=True` to avoid the extra LLM round-trip (typically 15–30 seconds for `qwen2.5:14b`).

A progress event `"Critic pass removed N false positive(s)"` is emitted when findings are actually removed, making it visible in the streaming UI.

---

### 8. AST-Based Plagiarism Similarity Hashing

**Area:** `agents/agent_14_plagiarism.py` + `database.py`

**Problem:** Plagiarism detection was limited to string-level pattern matching (boilerplate filenames, tutorial variable names, placeholder URLs). This cannot detect two students who submitted structurally identical code with renamed variables and different comments — the most common form of academic plagiarism.

**Fix — Structural Fingerprinting:**

**Python files (`.py`) — AST node sequence hashing:**
```python
tree = ast.parse(content)
node_types = [type(node).__name__ for node in ast.walk(tree)]
fingerprint = hashlib.md5(",".join(node_types).encode()).hexdigest()
```
Walking the AST and collecting node type names (`FunctionDef`, `Assign`, `For`, `Return`, ...) produces a sequence that is insensitive to variable names, comments, and whitespace but captures program structure. Two files with the same control flow, function shapes, and statement types will produce the same hash even if every identifier is renamed.

**JavaScript/TypeScript files (`.ts`/`.tsx`/`.js`/`.jsx`) — Token-bag hashing:**
Since Python has no built-in JS AST parser, a token-bag approach is used: extract all structural keywords (`function`, `class`, `const`, `if`, `for`, `async`, `await`, etc.) plus all identifiers longer than 3 characters, deduplicate and sort them, then hash the result:
```python
tokens = re.findall(r"\b(function|class|const|...) | \b[A-Za-z_]\w{3,}\b", content)
fingerprint = hashlib.md5(",".join(sorted(set(tokens))).encode()).hexdigest()
```
This is less precise than AST-based but still catches structurally identical files.

**Fix — Cross-Submission Comparison:**
Fingerprints are stored in the new `submission_fingerprints` table (added to `database.py`):

```sql
CREATE TABLE IF NOT EXISTS submission_fingerprints (
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    PRIMARY KEY (session_id, file_path)
);
CREATE INDEX IF NOT EXISTS idx_fingerprint ON submission_fingerprints(fingerprint);
```

For each file in the current submission, a lookup runs:
```sql
SELECT session_id FROM submission_fingerprints
WHERE fingerprint = ? AND session_id != ?
LIMIT 1
```

If a match is found in a previous submission, a descriptive match string is added to `tutorial_signals` and to the `cross_submission_matches` list in the originality report:

```
"File 'auth.py' has identical structure to submission a3f7b2c1..."
```

After comparison, the current submission's fingerprints are stored for future comparisons. This enables batch review scenarios where 30 students submit simultaneously — each submission is compared against all prior ones in the batch.

**Scoring impact:** Cross-submission matches are counted as tutorial signals, which feed into the originality penalty formula:
```python
penalty = min(30, len(tutorial_signals) * 5)
final_estimate = max(0, blended - penalty)
```
Each match reduces the originality score by up to 5 points (capped at -30).

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/review` | Start a new review (accepts `quick_mode` form field) |
| GET | `/review/{id}/stream` | SSE stream of agent progress |
| GET | `/review/{id}/report` | Full report JSON |
| POST | `/review/{id}/fix-suggestion` | Stream AI fix for a specific finding |
| POST | `/review/{id}/chat` | Stream AI chat about the report |
| POST | `/review/batch` | Submit multiple ZIPs for batch review |
| GET | `/api/profiles` | List all profiles |
| GET | `/api/rubrics` | List all rubrics |
| GET | `/health` | Backend + Ollama health check |
