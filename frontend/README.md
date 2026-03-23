# CodeProbe Frontend

React 19 + TypeScript + Vite + Tailwind v4 + Zustand

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (requires backend at http://localhost:8000)

## Development

```bash
npm run dev          # Dev server with HMR
npm run build        # TypeScript check + Vite build
npm run lint         # ESLint
```

## Testing

```bash
npm test             # Vitest unit tests
npm run test:watch   # Watch mode
npm run test:coverage  # Coverage report
npm run test:e2e     # Playwright E2E (requires running dev server)
```

---

## Architecture

```
src/
  components/
    layout/        AppShell, Sidebar, Header
    upload/        UploadPage, DropZone
    progress/      ProgressPage, AgentTimeline, LiveLog
    report/        ReportPage, all report section components
    batch/         BatchUploadPage, BatchProgressPage, ComparisonDashboard
    history/       HistoryPage, HistoryCard, ProgressChart, VersionComparison
    profiles/      ProfilesPage, ProfileEditor, RubricEditorModal
    chat/          ChatPanel, ChatMessageList, ChatInput
    codeviewer/    CodeViewerPanel (Monaco Editor)
    shared/        Badge, ProfileSelector, RubricSelector
  stores/
    reviewStore    SSE upload + pipeline state
    uiStore        Theme, navigation, toasts (persisted)
    batchStore     Batch review state
    historyStore   History + progress data
    profileStore   Profiles + rubrics CRUD
    chatStore      AI chat streaming state
  utils/
    csvExport      Download report as CSV
    pdfExport      html2canvas + jsPDF multi-page export
```

## Tech Stack

| Package | Purpose |
|---------|---------|
| React 19 + Vite | UI + build tool |
| TypeScript | Type safety |
| Tailwind v4 | Utility CSS (CSS-first, no config file) |
| Zustand | State management |
| Framer Motion | Animations |
| Recharts | Charts (radar, line, bar) |
| Monaco Editor | Read-only code viewer |
| react-diff-viewer-continued | Before/after fix diffs |
| Mermaid | Architecture diagram rendering |
| html2canvas + jsPDF | PDF export |

---

## Improvements & Technical Details

### 1. Fix Suggestion UI — SSE Payload Parsing Fix

**Files:** `src/components/report/FindingDiffView.tsx`, `src/components/report/FindingCard.tsx`

**Problem — SSE shape mismatch:**
The "Show Fix" button on every finding card opens a modal that calls `POST /review/{id}/fix-suggestion` and reads the streamed response. The backend emits a Server-Sent Event with the payload:

```json
data: {"type":"result","original_code":"...","fixed_code":"...","explanation":"..."}
```

The frontend event parser typed the event object as:
```typescript
{
  type: 'token' | 'complete' | 'error' | 'result';
  content?: string;
  message?: string;
  data?: FixResult;   // ← this field does not exist in the payload
}
```

The condition `if (event.type === 'result' && event.data)` was always false because `event.data` is `undefined` — the actual values are at `event.original_code`, `event.fixed_code`, and `event.explanation`. The diff viewer modal would render indefinitely in the loading state with no error.

**Fix:** Updated the event type to include the correct top-level fields:
```typescript
{
  type: 'token' | 'complete' | 'error' | 'result';
  content?: string;
  message?: string;
  original_code?: string;
  fixed_code?: string;
  explanation?: string;
}
```

The result is now built directly from these fields:
```typescript
if (event.type === 'result') {
  setResult({
    original_code: event.original_code ?? '',
    fixed_code:    event.fixed_code   ?? '',
    explanation:   event.explanation  ?? '',
  });
  setLoading(false);
}
```

**Problem — unstable finding ID breaks backend cache:**
`FindingCard.tsx` was passing `findingId={String(Math.random())}` to `FindingDiffView`. The backend caches fix results in memory keyed by `finding_id`. Because `Math.random()` generates a new value on every render, the cache was never hit — every click on "Show Fix" triggered a new Ollama call even for a finding the user had already asked about.

**Fix:** Changed to use the stable `finding.id` from the report data:
```tsx
findingId={finding.id}
```

This means repeated clicks on the same finding now return the cached result instantly without another LLM call.

---

### 2. Quick Mode — Frontend Wiring

**File:** `src/stores/reviewStore.ts`

**Problem:** `quickMode` was stored as a boolean in Zustand state and the toggle was rendered in `UploadPage.tsx`, but the value was never included in the `FormData` sent to the backend. The toggle had no effect.

**Fix:** In `startReview()`, `quickMode` is now read from store state alongside `uploads`:

```typescript
const { uploads, quickMode } = get();
```

It is conditionally appended to the form before the POST:

```typescript
if (quickMode) form.append('quick_mode', 'true');
```

The backend `review.py` reads this as `quick_mode: bool = Form(False)` and forwards it through the pipeline. See the backend README for the full pipeline-level implementation.

**User experience:** When Quick Mode is enabled, the review skips 5 agents and completes approximately 40–60% faster. The SSE progress stream includes `[quick mode]` in the pipeline start message so the user can confirm it was applied.

---

## State Management

All application state is managed by Zustand stores. Key flows:

### Review Flow (`reviewStore`)
1. User fills upload form → state stored in `uploads` slice
2. `startReview()` builds `FormData` (including `quick_mode` if set) and POSTs to `/review`
3. Backend returns `session_id`, frontend opens an `EventSource` to `/review/{id}/stream`
4. SSE events update `progress`, `phase`, and `agentTimeline` in real time
5. On `complete` event, report is fetched via `GET /review/{id}/report`

### Profile + Rubric Flow (`profileStore`)
1. `fetchProfiles()` calls `GET /api/profiles` → populates `profiles` list
2. `fetchRubrics()` calls `GET /api/rubrics` → populates `rubrics` list
3. Selected `profileId` and `rubricId` are included in the review `FormData`
4. The backend applies rubric weights to the score calculation (see backend README §3)

### Chat Flow (`chatStore`)
1. Chat panel sends `POST /review/{id}/chat` with message + history
2. Response is a token stream (`data: {"type":"token","content":"..."}`)
3. Tokens are appended to the current message in real time
4. On `complete`, the full message is saved to history

---

## API Base URL

Configured in `src/constants/config.ts`:

```typescript
export const API_BASE =
  (import.meta.env.VITE_API_BASE as string) ?? 'http://localhost:8000';
```

Override by setting `VITE_API_BASE` in a `.env` file:

```
VITE_API_BASE=http://my-backend-host:8000
```

**Route prefix note:** Profiles and rubrics are served under `/api/profiles` and `/api/rubrics`. All other routes (`/review`, `/history`, `/health`) have no `/api` prefix. This matches the backend router registration in `main.py`.
