# CodeReview Agent — Complete System Blueprint

> **16-Agent LangGraph Pipeline + 9 Advanced Features**
> Stack: React 18 + TypeScript + Vite + Tailwind + FastAPI + LangGraph + Ollama (100% Local)

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Agent Pipeline (16 Agents)](#2-agent-pipeline-16-agents)
3. [Backend API Surface](#3-backend-api-surface)
4. [Database Schema (SQLite)](#4-database-schema-sqlite)
5. [Frontend Project Structure](#5-frontend-project-structure)
6. [State Management (Zustand)](#6-state-management-zustand)
7. [SSE Integration & Event Protocol](#7-sse-integration--event-protocol)
8. [Page Flow & Screen Wireframes](#8-page-flow--screen-wireframes)
9. [Component Specifications](#9-component-specifications)
10. [Feature Specifications (9 Features)](#10-feature-specifications-9-features)
11. [Styling & Theming](#11-styling--theming)
12. [Responsive Layout Grid](#12-responsive-layout-grid)
13. [Animations & Micro-interactions](#13-animations--micro-interactions)
14. [Review Profiles & Rubric System](#14-review-profiles--rubric-system)
15. [Backend Implementation Details (All 16 Agents)](#15-backend-implementation-details-all-16-agents)
16. [Enhanced Report Structure](#16-enhanced-report-structure)
17. [Tech Stack & Dependencies](#17-tech-stack--dependencies)
18. [Development Setup](#18-development-setup)
19. [Testing Plan](#19-testing-plan)
20. [Implementation Phases](#20-implementation-phases)

---

## 1. System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + TypeScript + Vite)              │
│                                                                          │
│  Upload Zone → Progress Timeline → Report Dashboard → AI Chat → History │
│       │              ▲                    │                │              │
│       │              │ SSE                │ REST           │ SSE          │
└───────┼──────────────┼────────────────────┼────────────────┼─────────────┘
        │              │                    │                │
┌───────▼──────────────┴────────────────────▼────────────────▼─────────────┐
│                       BACKEND (FastAPI + LangGraph)                       │
│                                                                           │
│  ┌─────────┐   ┌───────────────────────────────────────────────────┐     │
│  │ Upload  │──▶│              LangGraph Pipeline                   │     │
│  │ Handler │   │                                                   │     │
│  └─────────┘   │  Extract ──▶ Structure ──┬──▶ React Evaluator     │     │
│                │                          ├──▶ FastAPI Evaluator    │     │
│  ┌─────────┐   │                          ├──▶ Security Scanner    │     │
│  │ Chat    │   │                          ├──▶ Performance Profiler│     │
│  │ Handler │   │                          ├──▶ Code Smell Detector │     │
│  └─────────┘   │                          ├──▶ Test Coverage       │     │
│                │                          ├──▶ Dependency Auditor  │     │
│  ┌─────────┐   │                          ├──▶ Accessibility Check │     │
│  │ History │   │                          └──▶ Documentation Scorer│     │
│  │ Handler │   │                               │ (fanin)           │     │
│  └─────────┘   │                          Integration Analyzer     │     │
│                │                          Requirements Validator    │     │
│  ┌─────────┐   │                          Plagiarism Detector      │     │
│  │ Batch   │   │                          Complexity Analyzer      │     │
│  │ Handler │   │                          Report Generator         │     │
│  └─────────┘   └───────────────────────────────────────────────────┘     │
│                                    │                                      │
│                              ┌─────▼─────┐    ┌──────────┐               │
│                              │  SQLite    │    │  Ollama  │               │
│                              │  History   │    │  (Local) │               │
│                              └───────────┘    └──────────┘               │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Pipeline (16 Agents)

### Execution Flow

```
Phase 1 — Sequential (must complete in order):
  Agent 1: Extract & Classify
  Agent 2: Structure Analyzer

Phase 2 — Parallel Fan-out (all run simultaneously after Phase 1):
  Agent 3:  React Evaluator
  Agent 4:  FastAPI Evaluator
  Agent 5:  Security Scanner
  Agent 6:  Performance Profiler
  Agent 7:  Code Smell Detector
  Agent 8:  Test Coverage Analyzer
  Agent 9:  Dependency Auditor
  Agent 10: Accessibility Checker
  Agent 11: Documentation Scorer

Phase 3 — Sequential (after fan-in of Phase 2):
  Agent 12: Integration Analyzer
  Agent 13: Requirements Validator (conditional — if problem statement provided)
  Agent 14: Plagiarism / Originality Detector
  Agent 15: Complexity Analyzer

Phase 4 — Final:
  Agent 16: Report Generator (enhanced — consumes all agent outputs)
```

### Agent Failure Isolation

If any Phase 2 agent raises an unhandled exception:
- LangGraph catches it and marks that agent as `{ "status": "error", "error": "message", "score": null }`
- Fan-in proceeds with the remaining successful agent outputs (partial report)
- Report Generator treats `null` scores as 0 for weighting, flags them as `"agent_failed"` in the report
- SSE emits `{ type: "error", agent: "<id>", message: "..." }` (non-fatal — pipeline continues)
- A fatal error (e.g. Ollama unreachable) emits `{ type: "error", message: "...", fatal: true }` and aborts

### Conditional Agent Activation

| Condition | Agents Skipped |
|---|---|
| No frontend files | React Evaluator, Accessibility Checker, FE perf checks |
| No backend files | FastAPI Evaluator, BE perf checks, partial Test Coverage |
| No test files at all | Test Coverage runs but reports "no tests found" |
| No problem statement | Requirements Validator |
| "Quick Mode" toggle | Only Structure + React + FastAPI + Integration + Report |
| "Beginner" profile | Complexity, Plagiarism, Dependency Auditor skipped |

### Agent Metadata Registry

```typescript
const AGENTS = [
  { id: "extract",        name: "Extract & Classify",       icon: "📂", phase: 1, description: "Unzip, build file tree, categorize FE/BE/Config" },
  { id: "structure",      name: "Structure Analyzer",        icon: "🏗️", phase: 1, description: "Parse deps, detect frameworks, evaluate organization" },
  { id: "react",          name: "React Evaluator",           icon: "⚛️", phase: 2, description: "Static + LLM deep review of React code" },
  { id: "fastapi",        name: "FastAPI Evaluator",         icon: "🐍", phase: 2, description: "Endpoint design, security, validation + LLM review" },
  { id: "security",       name: "Security Scanner",          icon: "🔒", phase: 2, description: "OWASP checks, secrets scan, taint analysis" },
  { id: "performance",    name: "Performance Profiler",      icon: "⚡", phase: 2, description: "Bundle size, re-renders, N+1 queries, blocking I/O" },
  { id: "codesmell",      name: "Code Smell Detector",       icon: "🦨", phase: 2, description: "God components, dead code, prop drilling, duplication" },
  { id: "testcoverage",   name: "Test Coverage Analyzer",    icon: "🧪", phase: 2, description: "Test ratio, quality, gap detection per critical path" },
  { id: "dependencies",   name: "Dependency Auditor",        icon: "📦", phase: 2, description: "Vulnerability, licensing, freshness, abandonment" },
  { id: "accessibility",  name: "Accessibility Checker",     icon: "♿", phase: 2, description: "WCAG 2.1 AA compliance, keyboard nav, ARIA" },
  { id: "documentation",  name: "Documentation Scorer",      icon: "📝", phase: 2, description: "README, docstrings, JSDoc, API docs completeness" },
  { id: "integration",    name: "Integration Analyzer",      icon: "🔗", phase: 3, description: "Map FE API calls ↔ BE endpoints, check contracts" },
  { id: "requirements",   name: "Requirements Validator",    icon: "📋", phase: 3, description: "Compare impl vs problem statement", conditional: true },
  { id: "plagiarism",     name: "Plagiarism Detector",       icon: "🔍", phase: 3, description: "Boilerplate %, tutorial signals, originality estimate" },
  { id: "complexity",     name: "Complexity Analyzer",       icon: "🧮", phase: 3, description: "Cyclomatic, cognitive, Halstead, maintainability index" },
  { id: "report",         name: "Report Generator",          icon: "📊", phase: 4, description: "Consolidate all scores, grade, executive summary" },
];
```

---

## 3. Backend API Surface

### Core Review APIs

```
POST /review
  Body: FormData {
    frontend_zip?: File,
    backend_zip?: File,
    combined_zip?: File,
    problem_statement?: string,
    profile_id?: string,          // Review profile to use
    rubric_id?: string,           // Custom rubric to apply
    student_name?: string,        // For history tracking
    project_id?: string,          // For re-review tracking
  }
  Response: { session_id, file_count }

GET  /review/{session_id}/stream
  Response: SSE stream (progress, result, report, error, complete events)

GET  /review/{session_id}/report
  Response: Full report JSON

GET  /review/{session_id}/file/{path}
  Response: { content, language, line_count }
  Purpose: Serve individual file for code viewer

GET  /review/{session_id}/validation/requirements
  Response: Parsed requirements from problem statement
  Purpose: Preview parsed requirements before/during review

GET  /review/{session_id}/validation/traceability
  Response: Traceability matrix (requirement → files mapping)
  Purpose: Standalone traceability view

GET  /review/{session_id}/validation/flows
  Response: E2E flow validations with step-by-step results
  Purpose: Standalone flow validation view

GET  /review/{session_id}/validation/test-scenarios
  Response: Generated test scenarios with pass/fail predictions
  Purpose: Standalone test scenario view

POST /review/{session_id}/validation/revalidate
  Body: { requirement_ids?: string[], updated_problem_statement?: string }
  Response: SSE stream of re-validation for specific requirements
  Purpose: Re-run validation after student explains intent or updates problem statement

POST /review/{session_id}/cancel
  Response: { ok: true }
  Purpose: Abort an in-progress LangGraph pipeline; transitions session to "cancelled" state
  Note: SSE stream will emit { type: "complete" } after cancellation is confirmed

POST /review/{session_id}/fix-suggestion
  Body: { finding_id: string, file: string, line: number, code_snippet: string, description: string }
  Response: SSE stream of Ollama fix generation
  Purpose: Generate before/after diff suggestion for a specific finding (cached per finding_id)
```

### AI Chat API

```
POST /review/{session_id}/chat
  Body: { message: string, history?: ChatMessage[] }
  Response: SSE stream of Ollama response with report context

  System context includes: full report JSON + code snippets for referenced findings
```

### Architecture Diagram API

```
GET  /review/{session_id}/diagram
  Response: { mermaid_code: string, diagram_type: "component_tree" | "api_flow" | "full_architecture" }

GET  /review/{session_id}/diagram/{type}
  Types: component_tree, api_flow, data_model, dependency_graph
  Response: { mermaid_code }
```

### Batch Review APIs

```
POST /review/batch
  Body: FormData {
    zips[]: File[],              // Multiple student zips
    student_names[]: string[],   // Parallel array of names
    problem_statement?: string,
    profile_id?: string,
    rubric_id?: string,
  }
  Response: { batch_id, student_count }

GET  /review/batch/{batch_id}/stream
  Response: SSE stream — events tagged with student_index
  Events: { type, student_index, agent?, message?, data? }

GET  /review/batch/{batch_id}/comparison
  Response: {
    students: [ { name, overall_score, grade, category_scores, critical_count } ],
    class_stats: { mean, median, std_dev, per_category },
    common_issues: [ { issue, frequency, affected_students } ],
    percentile_ranks: { student_name: percentile }
  }
```

### History & Progress APIs

```
GET  /history/{project_id}
  Query params: ?page=1&limit=20&student_name=&sort=created_at_desc
  Response: { items: [ { review_id, version, overall_score, grade, created_at } ], total, page, limit }

DELETE /history/{review_id}
  Response: { ok: true }
  Purpose: Remove a specific review record and its associated chat messages

GET  /history/{project_id}/progress
  Response: {
    versions: [ { version, scores_by_category, grade, date } ],
    trends: { improving: [...], declining: [...], stable: [...] },
    resolved_issues: [...],
    persistent_issues: [...],
    new_issues: [...]
  }

GET  /history/students/{student_name}
  Response: List of all reviews by this student across projects
```

### Profile & Rubric APIs

```
GET  /profiles
  Response: [ { id, name, description, strictness, agents_enabled, llm_tone } ]

GET  /profiles/{id}
  Response: Full profile configuration

POST /profiles
  Body: { name, description, agent_config, scoring_weights, llm_tone }
  Response: { id }

PUT  /profiles/{id}
  Body: { name, description, agent_config, scoring_weights, llm_tone }
  Response: { id }

DELETE /profiles/{id}
  Response: { ok: true }
  Note: Cannot delete built-in profiles (is_builtin = TRUE)

GET  /rubrics
  Response: [ { id, name, categories } ]

POST /rubrics
  Body: {
    name: string,
    categories: [ { name, weight, min_expectations: string } ]
  }
  Response: { id }

PUT  /rubrics/{id}
  Body: {
    name: string,
    categories: [ { name, weight, min_expectations: string } ]
  }
  Response: { id }

DELETE /rubrics/{id}
  Response: { ok: true }
```

### Health

```
GET  /health
  Response: { status, ollama, models[], active_model, db_status }
```

---

## 4. Database Schema (SQLite)

```sql
-- Review history for progress tracking
CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_id TEXT,
    student_name TEXT,
    version INTEGER DEFAULT 1,
    profile_id TEXT,
    rubric_id TEXT,
    overall_score REAL,
    grade TEXT,
    category_scores_json TEXT,        -- JSON of { category: score }
    report_json TEXT,                  -- Full report (compressed)
    file_count INTEGER,
    problem_statement TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_project_version ON reviews(project_id, version);
CREATE INDEX idx_student ON reviews(student_name, created_at);

-- Batch reviews
CREATE TABLE batch_reviews (
    id TEXT PRIMARY KEY,
    profile_id TEXT,
    rubric_id TEXT,
    problem_statement TEXT,
    student_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE batch_members (
    batch_id TEXT REFERENCES batch_reviews(id),
    review_id TEXT REFERENCES reviews(id),
    student_index INTEGER,
    PRIMARY KEY (batch_id, review_id)
);

-- Custom profiles
CREATE TABLE profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_builtin BOOLEAN DEFAULT FALSE,
    config_json TEXT,                  -- Agent toggles, weights, LLM tone
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Custom rubrics
CREATE TABLE rubrics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    categories_json TEXT,             -- [ { name, weight, min_expectations } ]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat history per review
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,                -- "user" | "assistant"
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_session ON chat_messages(session_id, created_at);

-- Seed built-in profiles
INSERT INTO profiles (id, name, description, is_builtin, config_json) VALUES
  ('beginner',    'Beginner Friendly',  'Lenient, encouraging, skips advanced checks',           TRUE, '{"strictness":"lenient","skip_agents":["complexity","plagiarism","dependencies"],"llm_tone":"encouraging and supportive"}'),
  ('bootcamp',    'Bootcamp Standard',  'Full-stack completeness, CRUD, basic auth',              TRUE, '{"strictness":"moderate","skip_agents":[],"llm_tone":"constructive and direct"}'),
  ('production',  'Production Ready',   'Security, performance, testing, error handling',          TRUE, '{"strictness":"strict","skip_agents":[],"llm_tone":"professional and thorough"}'),
  ('interview',   'Interview Prep',     'Code quality, patterns, complexity, best practices',      TRUE, '{"strictness":"strict","skip_agents":[],"llm_tone":"evaluative, like a senior interviewer"}'),
  ('hackathon',   'Hackathon',          'Creativity, completeness, demo-readiness',                TRUE, '{"strictness":"lenient","skip_agents":["plagiarism","documentation","accessibility"],"llm_tone":"enthusiastic and practical"}'),
  ('enterprise',  'Enterprise',         'Security, docs, testing, maintainability, CI/CD',         TRUE, '{"strictness":"very_strict","skip_agents":[],"llm_tone":"formal and compliance-focused"}');
```

---

## 5. Frontend Project Structure

```
src/
├── main.tsx
├── App.tsx
├── index.css                             # Tailwind + CSS variables
├── vite-env.d.ts
│
├── types/
│   ├── review.ts                         # ReviewState, Finding, AgentResult, Report
│   ├── agents.ts                         # Agent metadata types
│   ├── chat.ts                           # ChatMessage, ChatSession
│   ├── batch.ts                          # BatchReview, StudentComparison
│   ├── history.ts                        # ReviewVersion, ProgressData
│   ├── profiles.ts                       # Profile, Rubric, RubricCategory
│   └── api.ts                            # API request/response shapes
│
├── constants/
│   ├── agents.ts                         # AGENTS registry (id, name, icon, phase)
│   ├── config.ts                         # API_BASE, timeouts, limits
│   ├── gradeScale.ts                     # Grade boundaries + colors
│   └── owaspCategories.ts               # OWASP reference data for security panel
│
├── stores/
│   ├── reviewStore.ts                    # Main review state + actions
│   ├── chatStore.ts                      # AI chat state
│   ├── batchStore.ts                     # Batch review state
│   ├── historyStore.ts                   # Progress tracking state
│   ├── profileStore.ts                   # Profiles + rubrics state
│   └── uiStore.ts                        # Theme, sidebar, modals, active tab
│
├── services/
│   ├── api.ts                            # REST calls (upload, health, profiles, rubrics, history)
│   ├── sse.ts                            # EventSource wrapper with reconnect + typed events
│   ├── batchApi.ts                       # Batch upload + comparison fetch
│   ├── chatApi.ts                        # Chat SSE stream
│   └── fileApi.ts                        # Fetch individual file content for code viewer
│
├── hooks/
│   ├── useReviewStream.ts                # SSE lifecycle for single review
│   ├── useBatchStream.ts                 # SSE lifecycle for batch review
│   ├── useChatStream.ts                  # SSE lifecycle for AI chat
│   ├── useHealthCheck.ts                 # Polls /health on mount
│   ├── useProfiles.ts                    # Fetch + manage profiles
│   ├── useRubrics.ts                     # Fetch + manage rubrics
│   ├── useHistory.ts                     # Fetch review history + progress
│   └── useCodeViewer.ts                  # Fetch file + map findings to line annotations
│
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx                  # Sidebar + main content area
│   │   ├── Sidebar.tsx                   # Navigation: Review, Batch, History, Profiles
│   │   ├── Header.tsx                    # Title, Ollama status LED, theme toggle
│   │   └── Footer.tsx                    # Version, credits
│   │
│   ├── upload/
│   │   ├── UploadPage.tsx                # Full upload screen composition
│   │   ├── UploadModeToggle.tsx          # Combined vs Separate toggle
│   │   ├── DropZone.tsx                  # Drag-and-drop (react-dropzone)
│   │   ├── FilePreview.tsx               # Selected file: name, size, remove
│   │   ├── ProblemStatementInput.tsx     # Textarea for problem statement
│   │   ├── ProfileSelector.tsx           # Dropdown to pick review profile
│   │   ├── RubricSelector.tsx            # Dropdown to pick or create rubric
│   │   ├── StudentInfoFields.tsx         # Student name + project ID (for history)
│   │   ├── QuickModeToggle.tsx           # Toggle for reduced agent set
│   │   └── SubmitButton.tsx              # Submit with validation + loading state
│   │
│   ├── progress/
│   │   ├── ProgressPage.tsx              # Full progress screen composition
│   │   ├── AgentTimeline.tsx             # Vertical stepper with phase grouping
│   │   ├── AgentStep.tsx                 # Single agent: icon, label, status, message
│   │   ├── PhaseGroup.tsx                # Groups agents by phase (1-4) with phase label
│   │   ├── ParallelIndicator.tsx         # Visual indicator that Phase 2 agents run in parallel
│   │   ├── LiveLog.tsx                   # Scrolling text log of all progress messages
│   │   ├── PartialResultPreview.tsx      # Collapsed preview of completed agent results
│   │   └── CancelButton.tsx             # Abort review
│   │
│   ├── report/
│   │   ├── ReportPage.tsx                # Full report screen composition
│   │   ├── OverallScoreCard.tsx          # Radial gauge + grade badge
│   │   ├── CategoryScoresGrid.tsx        # Grid of all category score bars
│   │   ├── CategoryScoreBar.tsx          # Single horizontal bar with score label
│   │   ├── ExecutiveSummary.tsx          # LLM markdown rendered
│   │   ├── PriorityActionItems.tsx       # Top 5 fix recommendations with time estimates
│   │   ├── StrengthsHighlight.tsx        # Positive findings showcase
│   │   │
│   │   ├── findings/
│   │   │   ├── FindingsPanel.tsx         # Tabbed: Critical / Suggestions / Strengths
│   │   │   ├── FindingCard.tsx           # Single finding with type icon, area badge, detail
│   │   │   ├── FindingCodeLink.tsx       # Clickable file:line link → opens code viewer
│   │   │   └── FindingDiffView.tsx       # Before/After fix suggestion (react-diff-viewer)
│   │   │
│   │   ├── security/
│   │   │   ├── SecurityReport.tsx        # Security scanner dedicated section
│   │   │   ├── SeverityBreakdown.tsx     # Critical/High/Medium/Low counts
│   │   │   ├── OwaspCoverage.tsx         # OWASP top-10 checklist with status
│   │   │   └── SecurityFindingCard.tsx   # Finding with severity, OWASP ref, fix
│   │   │
│   │   ├── performance/
│   │   │   ├── PerformanceReport.tsx     # FE + BE performance findings
│   │   │   ├── BundleImpactChart.tsx     # Estimated bundle size breakdown
│   │   │   ├── RerenderRisks.tsx         # List of rerender traps
│   │   │   └── BackendBottlenecks.tsx    # N+1, blocking I/O, missing cache
│   │   │
│   │   ├── codequality/
│   │   │   ├── CodeSmellReport.tsx       # Code smell findings
│   │   │   ├── SmellDensityChart.tsx     # Smells per 100 lines over files
│   │   │   ├── ComplexityReport.tsx      # Complexity metrics dashboard
│   │   │   ├── ComplexityDistribution.tsx # Bar chart: low/moderate/high/danger
│   │   │   ├── MostComplexFunctions.tsx  # Ranked table of top-N complex functions
│   │   │   └── RefactoringSuggestions.tsx # LLM-generated refactoring advice
│   │   │
│   │   ├── testing/
│   │   │   ├── TestCoverageReport.tsx    # Test analysis dashboard
│   │   │   ├── CoverageGapMatrix.tsx     # Source module → has test? critical?
│   │   │   ├── TestQualityMetrics.tsx    # Assertions/test, snapshot %, mock %
│   │   │   └── MissingTestsList.tsx      # Critical paths without tests
│   │   │
│   │   ├── integration/
│   │   │   ├── IntegrationReport.tsx     # Integration analysis section
│   │   │   ├── EndpointMap.tsx           # Two-column FE↔BE visual mapping
│   │   │   ├── ContractMismatches.tsx    # LLM-identified data shape issues
│   │   │   └── BaseUrlStatus.tsx         # Centralized API config check
│   │   │
│   │   ├── requirements/
│   │   │   ├── FunctionalValidationReport.tsx  # Full functional validation section
│   │   │   ├── RequirementsSummaryCards.tsx     # Must-have/should-have/nice-to-have stats
│   │   │   ├── RequirementsTable.tsx            # Requirement → Status → Score → Evidence
│   │   │   ├── RequirementDetailModal.tsx       # Deep dive per requirement (criteria, bugs, evidence)
│   │   │   ├── CriteriaChecklist.tsx            # Per-requirement acceptance criteria with pass/fail
│   │   │   ├── TraceabilityMatrix.tsx           # Requirement → FE files → BE files → Test files
│   │   │   ├── FlowValidationTimeline.tsx       # End-to-end flow step visualization
│   │   │   ├── FlowBreakpointIndicator.tsx      # Visual "flow breaks here" marker
│   │   │   ├── TestScenarioPanel.tsx            # Generated test scenarios (would pass/fail)
│   │   │   ├── TestScenarioCard.tsx             # Single test: happy/edge/negative + pass prediction
│   │   │   ├── CompletenessBar.tsx              # Percentage bar (completeness + correctness)
│   │   │   ├── GapAnalysisPanel.tsx             # Missing, partial, incorrect, extra features
│   │   │   ├── PriorityFixesList.tsx            # Ordered list of fixes with effort estimates
│   │   │   ├── BugsFoundTable.tsx               # Bugs discovered during validation with severity
│   │   │   ├── FunctionalScoreBreakdown.tsx     # Score formula visualization
│   │   │   ├── RevalidatePanel.tsx              # "Student explains intent" input + re-run button
│   │   │   └── RevalidateStream.tsx             # SSE progress for revalidation of specific reqs
│   │   │
│   │   ├── documentation/
│   │   │   ├── DocumentationReport.tsx   # Docs scoring section
│   │   │   ├── ReadmeChecklist.tsx       # README section presence checklist
│   │   │   ├── DocstringCoverage.tsx     # Python + TS docstring coverage bars
│   │   │   └── ApiDocsStatus.tsx         # FastAPI /docs completeness
│   │   │
│   │   ├── accessibility/
│   │   │   ├── AccessibilityReport.tsx   # A11y findings section
│   │   │   ├── WcagSummary.tsx           # A / AA / AAA status badges
│   │   │   └── A11yViolationCard.tsx     # Violation with impact, rule, fix
│   │   │
│   │   ├── dependencies/
│   │   │   ├── DependencyReport.tsx      # Dependency audit section
│   │   │   ├── DependencyHealthTable.tsx # Package → status → concern
│   │   │   └── VulnerabilityAlerts.tsx   # Known CVE / abandoned package alerts
│   │   │
│   │   ├── originality/
│   │   │   ├── OriginalityReport.tsx     # Plagiarism detector section
│   │   │   ├── OriginalityGauge.tsx      # Originality % radial
│   │   │   ├── BoilerplateBreakdown.tsx  # Custom vs template code ratio
│   │   │   └── TutorialSignals.tsx       # Detected tutorial patterns
│   │   │
│   │   ├── architecture/
│   │   │   ├── ArchitectureDiagram.tsx   # Mermaid.js rendered diagram
│   │   │   ├── DiagramTypeSelector.tsx   # Toggle: component tree / API flow / full
│   │   │   └── MermaidRenderer.tsx       # Generic mermaid → SVG renderer
│   │   │
│   │   ├── structure/
│   │   │   ├── StructureReport.tsx       # Project structure section
│   │   │   ├── FileStatsCards.tsx        # FE/BE file count, line count cards
│   │   │   ├── FrameworkBadges.tsx       # Detected frameworks as badges
│   │   │   ├── FolderChecklist.tsx       # has_components, has_tests, etc.
│   │   │   └── CodeHeatmap.tsx           # Heat map: files colored by issue density
│   │   │
│   │   └── export/
│   │       ├── ExportPanel.tsx           # Export buttons row
│   │       ├── ExportJson.tsx            # Download report JSON
│   │       ├── ExportPdf.tsx             # html2canvas + jsPDF capture
│   │       ├── ExportCsv.tsx             # Export scores as CSV (batch mode)
│   │       └── CopySummary.tsx           # Copy executive summary to clipboard
│   │
│   ├── codeviewer/
│   │   ├── CodeViewerPanel.tsx           # Slide-out side panel
│   │   ├── CodeEditor.tsx                # Monaco Editor (read-only) with syntax highlighting
│   │   ├── GutterAnnotations.tsx         # Red/amber/green markers per finding line
│   │   ├── FindingTooltip.tsx            # Hover tooltip on annotated line
│   │   └── IssueNavigator.tsx            # Jump to next/prev issue buttons
│   │
│   ├── chat/
│   │   ├── ChatPanel.tsx                 # Slide-out right panel or bottom drawer
│   │   ├── ChatMessageList.tsx           # Scrollable message list
│   │   ├── ChatMessage.tsx               # Single message bubble (user or assistant)
│   │   ├── ChatInput.tsx                 # Text input + send button
│   │   ├── SuggestedQuestions.tsx         # Quick-action chips based on findings
│   │   └── ChatCodeBlock.tsx             # Syntax-highlighted code in chat responses
│   │
│   ├── batch/
│   │   ├── BatchUploadPage.tsx           # Multi-student upload screen
│   │   ├── BatchDropZone.tsx             # Multi-file drop zone
│   │   ├── StudentList.tsx               # List of uploaded zips with name fields
│   │   ├── BatchProgressPage.tsx         # Multi-student progress tracking
│   │   ├── BatchStudentRow.tsx           # Single student progress row
│   │   ├── ComparisonDashboard.tsx       # Class-wide comparison matrix
│   │   ├── ComparisonTable.tsx           # Student × category scores table
│   │   ├── ClassStatsCards.tsx           # Mean, median, std dev per category
│   │   ├── CommonIssuesPanel.tsx         # Issues that appear across multiple students
│   │   ├── PercentileChart.tsx           # Student ranking visualization
│   │   └── BatchExport.tsx               # Export comparison as CSV
│   │
│   ├── history/
│   │   ├── HistoryPage.tsx               # Review history browser
│   │   ├── HistoryList.tsx               # List of past reviews with scores
│   │   ├── HistoryCard.tsx               # Single review: date, score, grade, link
│   │   ├── ProgressChart.tsx             # Score trend line chart across versions
│   │   ├── VersionComparison.tsx         # Side-by-side v1 vs v2 score diff
│   │   ├── ResolvedIssues.tsx            # Issues fixed since last version
│   │   ├── PersistentIssues.tsx          # Issues that remain across versions
│   │   └── NewIssues.tsx                 # Issues introduced in latest version
│   │
│   ├── learningpath/
│   │   ├── LearningPathPanel.tsx         # Learning path section in report
│   │   ├── WeekPlan.tsx                  # Single week's learning items
│   │   ├── LearningItem.tsx              # Topic, why, exercise, time estimate
│   │   └── SkillGapRadar.tsx             # Radar chart of skill areas
│   │
│   ├── profiles/
│   │   ├── ProfilesPage.tsx              # Profile management screen
│   │   ├── ProfileCard.tsx               # Single profile: name, description, strictness
│   │   ├── ProfileEditor.tsx             # Create/edit profile form
│   │   ├── AgentToggleList.tsx           # Toggle agents on/off per profile
│   │   ├── WeightSliders.tsx             # Adjust category weights
│   │   ├── RubricEditor.tsx              # Create/edit rubric
│   │   └── RubricCategoryRow.tsx         # Single rubric row: name, weight, expectations
│   │
│   └── shared/
│       ├── RadialGauge.tsx               # Recharts radial bar for scores
│       ├── ScoreBar.tsx                  # Horizontal progress bar
│       ├── Badge.tsx                     # Colored status badge
│       ├── SeverityBadge.tsx             # Critical/High/Medium/Low badge
│       ├── Accordion.tsx                 # Expandable section
│       ├── Tabs.tsx                      # Tab switcher
│       ├── Tooltip.tsx                   # Hover tooltip
│       ├── Modal.tsx                     # Centered modal overlay
│       ├── SlidePanel.tsx                # Slide-in side panel (for code viewer, chat)
│       ├── MarkdownRenderer.tsx          # Renders LLM markdown safely (react-markdown)
│       ├── EmptyState.tsx                # Illustration for no-data states
│       ├── Toast.tsx                     # Notification toast
│       ├── LoadingSpinner.tsx            # Consistent spinner
│       ├── StatusDot.tsx                 # Green/red/amber dot
│       ├── DataTable.tsx                 # Generic sortable table
│       ├── SearchInput.tsx               # Search/filter input
│       └── ConfirmDialog.tsx             # Confirmation modal for destructive actions
│
└── utils/
    ├── gradeColor.ts                     # Grade → color mapping
    ├── scoreColor.ts                     # Score → gradient color (red-amber-green)
    ├── formatScore.ts                    # Score formatting (1 decimal)
    ├── formatBytes.ts                    # File size formatting
    ├── formatDuration.ts                 # Time formatting
    ├── fileHelpers.ts                    # Zip validation, extension checks
    ├── mermaidHelper.ts                  # Mermaid initialization + render
    ├── diffHelper.ts                     # Code diff computation
    ├── csvExport.ts                      # Generate CSV from data
    └── pdfExport.ts                      # html2canvas + jsPDF logic
```

---

## 6. State Management (Zustand)

### `reviewStore.ts` — Main Review State

```
State Shape:
├── phase: "idle" | "uploading" | "reviewing" | "complete" | "error"
├── sessionId: string | null
├── quickMode: boolean
│
├── uploads: {
│   ├── mode: "combined" | "separate"
│   ├── combinedZip: File | null
│   ├── frontendZip: File | null
│   ├── backendZip: File | null
│   ├── problemStatement: string
│   ├── studentName: string
│   ├── projectId: string
│   ├── profileId: string           // Selected review profile
│   └── rubricId: string | null     // Optional custom rubric
│   }
│
├── progress: {
│   ├── currentAgent: string
│   ├── currentPhase: 1 | 2 | 3 | 4
│   ├── messages: Array<{ agent, message, timestamp }>
│   └── agentStatuses: Record<agentId, "pending"|"running"|"done"|"error"|"skipped">
│   }
│
├── partialResults: Record<agentId, any>
│
├── report: FullReport | null        // Set when report event arrives
│
├── codeViewer: {
│   ├── isOpen: boolean
│   ├── filePath: string | null
│   ├── fileContent: string | null
│   ├── language: string
│   ├── annotations: Array<{ line, severity, message }>
│   └── activeFindingIndex: number
│   }
│
└── error: string | null

Actions:
├── setUploadField(field, value)
├── startReview()                     // POST → get sessionId → open SSE
├── handleSSEEvent(event)             // Route to correct handler
├── cancelReview()                    // POST /review/{id}/cancel → close SSE → reset to idle
├── openCodeViewer(filePath, findings)
├── closeCodeViewer()
├── navigateFinding(direction)        // Next/prev in code viewer
├── reset()                           // Back to idle
└── setQuickMode(enabled)
```

### `chatStore.ts` — AI Chat State

```
State Shape:
├── isOpen: boolean
├── messages: ChatMessage[]
├── isStreaming: boolean
├── suggestedQuestions: string[]
└── error: string | null

Actions:
├── openChat()
├── closeChat()
├── sendMessage(text)                 // POST SSE → stream response
├── appendToken(token)                // Streaming append
├── finishStream()
└── clearChat()
```

### `batchStore.ts` — Batch Review State

```
State Shape:
├── phase: "idle" | "uploading" | "reviewing" | "complete" | "error"
├── batchId: string | null
├── problemStatement: string          // Shared problem statement for all students in batch
├── profileId: string
├── rubricId: string | null
├── concurrencyLimit: number          // Max parallel student pipelines (default: 3)
├── students: Array<{
│     name: string,
│     file: File,
│     status: "pending"|"reviewing"|"complete"|"error",
│     currentAgent: string | null,
│     score: number | null,
│     grade: string | null
│   }>
├── comparison: ComparisonData | null
└── error: string | null

Actions:
├── addStudentFiles(files: File[])
├── setStudentName(index, name)
├── removeStudent(index)
├── startBatchReview()
├── handleBatchSSE(event)
├── fetchComparison()
└── reset()
```

### `historyStore.ts` — History & Progress State

```
State Shape:
├── reviews: ReviewSummary[]
├── selectedProjectId: string | null
├── progressData: ProgressData | null
├── isLoading: boolean
└── error: string | null

Actions:
├── fetchHistory(projectId)
├── fetchStudentHistory(studentName)
├── fetchProgress(projectId)
├── selectReview(reviewId)            // Navigate to past report
└── clearHistory()
```

### `profileStore.ts` — Profiles & Rubrics State

```
State Shape:
├── profiles: Profile[]
├── rubrics: Rubric[]
├── selectedProfileId: string
├── selectedRubricId: string | null
├── editingProfile: Profile | null
├── editingRubric: Rubric | null
└── isLoading: boolean

Actions:
├── fetchProfiles()
├── fetchRubrics()
├── createProfile(config)
├── updateProfile(id, config)
├── createRubric(config)
├── updateRubric(id, config)
├── deleteProfile(id)
├── deleteRubric(id)
├── selectProfile(id)
└── selectRubric(id)
```

### `uiStore.ts` — UI State

```
Persistence: use zustand/middleware persist — serialize { theme } to localStorage key "ui-prefs"

State Shape:
├── theme: "dark" | "light"
├── sidebarOpen: boolean
├── activePage: "review" | "batch" | "history" | "profiles"
├── activeReportTab: string
├── toasts: Toast[]
└── confirmDialog: { open, title, message, onConfirm } | null

Actions:
├── toggleTheme()
├── toggleSidebar()
├── navigate(page)
├── showToast(message, type)
├── showConfirm(title, message, onConfirm)
└── dismissToast(id)
```

---

## 7. SSE Integration & Event Protocol

### Single Review SSE Events

```typescript
// Event types streamed from GET /review/{id}/stream
type SSEEvent =
  | { type: "progress"; agent: string; phase: number; message: string }
  | { type: "result";   agent: string; data: AgentResult }
  | { type: "report";   data: FullReport }
  | { type: "error";    message: string }
  | { type: "complete" }
```

### Batch Review SSE Events

```typescript
// Event types streamed from GET /review/batch/{id}/stream
type BatchSSEEvent =
  | { type: "student_start";    student_index: number; student_name: string }
  | { type: "student_progress"; student_index: number; agent: string; message: string }
  | { type: "student_result";   student_index: number; agent: string; data: AgentResult }
  | { type: "student_complete"; student_index: number; overall_score: number; grade: string }
  | { type: "student_error";    student_index: number; message: string }
  | { type: "batch_complete";   comparison: ComparisonData }
  | { type: "error";            message: string }
```

### Chat SSE Events

```typescript
// Streamed from POST /review/{id}/chat
type ChatSSEEvent =
  | { type: "token"; content: string }     // Streaming token
  | { type: "done" }                       // Response complete
  | { type: "error"; message: string }
```

### SSE Wrapper (`sse.ts`)

Responsibilities:
- Creates EventSource with correct URL
- Parses `data:` JSON lines
- Dispatches typed events to callback
- Auto-reconnect with exponential backoff (max 3 retries, 1s → 2s → 4s)
- Cleanup on unmount or manual close
- Timeout detection (if no event for 120s, reconnect)

**Batch SSE reconnect** (`useBatchStream.ts`):
- Same backoff policy as single review (max 3 retries, 1s → 2s → 4s)
- On reconnect, backend replays `student_start` + `student_complete` events for
  already-finished students so the frontend can restore correct per-student state
- If reconnect fails after 3 attempts, marks all in-progress students as `"error"`
  and surfaces a retry button

---

## 8. Page Flow & Screen Wireframes

### Navigation Structure

```
Sidebar:
├── 📝 New Review       → UploadPage
├── 👥 Batch Review     → BatchUploadPage
├── 📈 History          → HistoryPage
├── ⚙️ Profiles         → ProfilesPage
└── Status: Ollama LED
```

### Screen 1: Upload (phase = "idle")

```
┌──────────────────────────────────────────────────────────────────┐
│  Sidebar  │                                                      │
│           │  ┌─ Upload Mode ────────────────────────────────┐    │
│  📝 Review│  │  [Combined Zip]  |  [Separate FE + BE]      │    │
│  👥 Batch │  └──────────────────────────────────────────────┘    │
│  📈 Hist  │                                                      │
│  ⚙️ Prof  │  ┌─ Drop Zone ─────────────────────────────────┐    │
│           │  │                                              │    │
│           │  │   ☁️  Drag & drop zip file(s) here           │    │
│           │  │       or click to browse                     │    │
│           │  │       .zip | Max 50MB                        │    │
│           │  │                                              │    │
│           │  └──────────────────────────────────────────────┘    │
│           │                                                      │
│           │  ┌─ Selected Files ─────────────────────────────┐    │
│           │  │  📦 project.zip  (3.1 MB)            [✕]    │    │
│           │  └──────────────────────────────────────────────┘    │
│           │                                                      │
│           │  ┌─ Configuration ──────────────────────────────┐    │
│           │  │                                              │    │
│           │  │  Profile: [Bootcamp Standard ▾]              │    │
│           │  │  Rubric:  [None (default weights) ▾]         │    │
│           │  │  ☐ Quick Mode (reduced agent set)            │    │
│           │  │                                              │    │
│           │  │  Student Name: [______________]              │    │
│           │  │  Project ID:   [______________]              │    │
│           │  │  (for progress tracking across versions)     │    │
│           │  │                                              │    │
│           │  └──────────────────────────────────────────────┘    │
│           │                                                      │
│           │  ┌─ Problem Statement (Optional) ───────────────┐    │
│           │  │                                              │    │
│           │  │  Paste the assignment/problem statement to   │    │
│           │  │  validate implementation against             │    │
│           │  │  requirements...                             │    │
│           │  │                                              │    │
│           │  └──────────────────────────────────────────────┘    │
│           │                                                      │
│  ● Ollama │         [ 🚀 Start Code Review ]                     │
│    Online │                                                      │
└───────────┴──────────────────────────────────────────────────────┘
```

### Screen 2: Review Progress (phase = "reviewing")

```
┌──────────────────────────────────────────────────────────────────┐
│  Sidebar  │                                                      │
│           │  ┌─ Agent Pipeline ─────────────────────────────┐    │
│           │  │                                              │    │
│           │  │  Phase 1 — Setup                             │    │
│           │  │  ✅ Extract & Classify                       │    │
│           │  │     "📂 Extracted 47 files"                  │    │
│           │  │  ✅ Structure Analyzer                       │    │
│           │  │     "🏗️ React+TS | FastAPI+SQLAlchemy"       │    │
│           │  │                                              │    │
│           │  │  Phase 2 — Deep Analysis (parallel)    ⚡    │    │
│           │  │  ✅ React Evaluator         7.2/10          │    │
│           │  │  🔄 FastAPI Evaluator       analyzing...     │    │
│           │  │  🔄 Security Scanner        scanning...      │    │
│           │  │  🔄 Performance Profiler    profiling...     │    │
│           │  │  ⏳ Code Smell Detector                      │    │
│           │  │  ⏳ Test Coverage                            │    │
│           │  │  ⏳ Dependency Auditor                       │    │
│           │  │  ⏳ Accessibility Checker                    │    │
│           │  │  ⏳ Documentation Scorer                     │    │
│           │  │                                              │    │
│           │  │  Phase 3 — Cross-Analysis                    │    │
│           │  │  ⏳ Integration Analyzer                     │    │
│           │  │  ⏳ Requirements Validator                   │    │
│           │  │  ⏳ Plagiarism Detector                      │    │
│           │  │  ⏳ Complexity Analyzer                      │    │
│           │  │                                              │    │
│           │  │  Phase 4 — Report                            │    │
│           │  │  ⏳ Report Generator                         │    │
│           │  │                                              │    │
│           │  └──────────────────────────────────────────────┘    │
│           │                                                      │
│           │  ┌─ Live Log ───────────────────────────────────┐    │
│           │  │  [10:23:01] Extract: 47 files processed      │    │
│           │  │  [10:23:03] Structure: React + FastAPI...     │    │
│           │  │  [10:23:05] React: Analyzing hooks...         │    │
│           │  │  [10:23:05] Security: Scanning secrets...     │    │
│           │  │  █                                           │    │
│           │  └──────────────────────────────────────────────┘    │
│           │                                                      │
│           │  Estimated: 3-5 min  |  [Cancel Review]              │
└───────────┴──────────────────────────────────────────────────────┘
```

### Screen 3: Report Dashboard (phase = "complete")

```
┌──────────────────────────────────────────────────────────────────────┐
│ Sidebar │                                              [💬 Ask AI]  │
│         │  ┌─ Score ──────┐  ┌─ Category Scores ─────────────────┐  │
│         │  │   ╭─────╮    │  │ Code Quality    ████████░░ 7.2    │  │
│         │  │   │ 6.8 │    │  │ Security        ██████░░░░ 5.8    │  │
│         │  │   │ /10 │    │  │ Architecture    ████████░░ 7.5    │  │
│         │  │   ╰─────╯    │  │ React           █████████░ 8.1    │  │
│         │  │   Grade: B   │  │ FastAPI          ██████░░░░ 6.0    │  │
│         │  └──────────────┘  │ Testing          ████░░░░░░ 3.5    │  │
│         │                    │ Performance      ███████░░░ 6.8    │  │
│         │                    │ Documentation    █████░░░░░ 4.8    │  │
│         │                    │ Accessibility    ██████░░░░ 5.5    │  │
│         │                    │ Originality      ████████░░ 7.0    │  │
│         │                    └────────────────────────────────────┘  │
│         │                                                            │
│         │  ┌─ Priority Action Items ─────────────────────────────┐  │
│         │  │ 1. 🔴 Add Error Boundaries           ~2 hrs        │  │
│         │  │ 2. 🔴 Fix SQL injection in orders.py  ~1 hr        │  │
│         │  │ 3. 🟡 Add tests for auth endpoints    ~3 hrs       │  │
│         │  │ 4. 🟡 Extract god component Dashboard ~2 hrs       │  │
│         │  │ 5. 🟡 Add Pydantic response models    ~1 hr        │  │
│         │  └─────────────────────────────────────────────────────┘  │
│         │                                                            │
│         │  ┌─ Executive Summary ─────────────────────────────────┐  │
│         │  │ (LLM markdown — 3-4 paragraphs)                    │  │
│         │  └─────────────────────────────────────────────────────┘  │
│         │                                                            │
│         │  ┌─ Findings [🔴 8] [💡 15] [✅ 11] ──────────────────┐  │
│         │  │ 🔴 Security — Hardcoded API key in config.py:14    │  │
│         │  │    Fix: Move to env variable     [View Code →]     │  │
│         │  │    [Show Fix ▾] ← expands diff view                │  │
│         │  │                                                     │  │
│         │  │ 🔴 Error Handling — No Error Boundary               │  │
│         │  │    [View Code →]  [Show Fix ▾]                      │  │
│         │  └─────────────────────────────────────────────────────┘  │
│         │                                                            │
│         │  ▶ Security Report (OWASP coverage, severity breakdown)   │
│         │  ▶ Performance Report (bundle, rerenders, N+1)            │
│         │  ▶ Code Quality (smells, complexity, refactoring)          │
│         │  ▶ Test Coverage (gaps, quality, missing tests)            │
│         │  ▶ Integration Map (FE ↔ BE endpoint mapping)             │
│         │  ▶ Architecture Diagram (auto-generated Mermaid)           │
│         │  ▶ Requirements Validation (if provided)                   │
│         │     ┌─ Functional Validation Dashboard ───────────────┐    │
│         │     │                                                  │    │
│         │     │  ┌── Summary Cards ─────────────────────────┐   │    │
│         │     │  │ Must-Have: 5/8 met  │ Should: 2/3  │ ...│   │    │
│         │     │  └──────────────────────────────────────────┘   │    │
│         │     │                                                  │    │
│         │     │  Completeness: ████████░░ 72%                   │    │
│         │     │  Correctness:  ██████░░░░ 68%                   │    │
│         │     │  Test Pass:    ███████░░░ 75%                   │    │
│         │     │                                                  │    │
│         │     │  ┌── Requirements Table ────────────────────┐   │    │
│         │     │  │ ID    Requirement        Status   Score  │   │    │
│         │     │  │ R001  User Registration  ⚠️ Part   7.5  │   │    │
│         │     │  │ R002  User Login         ✅ Met    9.0  │   │    │
│         │     │  │ R003  Task CRUD          ⚠️ Part   6.0  │   │    │
│         │     │  │ R004  Role-Based Access  ❌ Miss   0.0  │   │    │
│         │     │  │ R005  Search & Filter    ✅ Met    8.5  │   │    │
│         │     │  │ [Click any row → deep dive modal]        │   │    │
│         │     │  └──────────────────────────────────────────┘   │    │
│         │     │                                                  │    │
│         │     │  ┌── Requirement Detail Modal (R001) ──────┐   │    │
│         │     │  │ User Registration                        │   │    │
│         │     │  │                                          │   │    │
│         │     │  │ Acceptance Criteria:                     │   │    │
│         │     │  │ ✅ Registration form exists               │   │    │
│         │     │  │ ✅ Email validation                       │   │    │
│         │     │  │ ⚠️ Password validation (no strength chk) │   │    │
│         │     │  │ ❌ Duplicate email prevention             │   │    │
│         │     │  │ ✅ Success confirmation                   │   │    │
│         │     │  │                                          │   │    │
│         │     │  │ Evidence:                                │   │    │
│         │     │  │ FE: Register.tsx:15-45    [View Code →]  │   │    │
│         │     │  │ BE: auth.py:20-35         [View Code →]  │   │    │
│         │     │  │ DB: user.py:5-15          [View Code →]  │   │    │
│         │     │  │                                          │   │    │
│         │     │  │ 🐛 Bugs Found:                           │   │    │
│         │     │  │ CRITICAL: No unique constraint on email  │   │    │
│         │     │  │ Fix: Add unique=True to User.email       │   │    │
│         │     │  │ Effort: ~30 minutes                      │   │    │
│         │     │  └──────────────────────────────────────────┘   │    │
│         │     │                                                  │    │
│         │     │  ┌── Traceability Matrix ───────────────────┐   │    │
│         │     │  │ Req   FE Files       BE Files    Tests   │   │    │
│         │     │  │ R001  Register.tsx   auth.py     ❌ none │   │    │
│         │     │  │ R002  Login.tsx      auth.py     ✅ 2    │   │    │
│         │     │  │ R003  TaskList.tsx   tasks.py    ⚠️ 1    │   │    │
│         │     │  │       TaskForm.tsx   task_svc.py          │   │    │
│         │     │  └──────────────────────────────────────────┘   │    │
│         │     │                                                  │    │
│         │     │  ┌── E2E Flow Validation ───────────────────┐   │    │
│         │     │  │                                          │   │    │
│         │     │  │ Flow: Register → Login → Create Task     │   │    │
│         │     │  │                                          │   │    │
│         │     │  │ ✅ Step 1: Fill registration form         │   │    │
│         │     │  │ │                                        │   │    │
│         │     │  │ ✅ Step 2: POST /register                 │   │    │
│         │     │  │ │                                        │   │    │
│         │     │  │ ✅ Step 3: Backend creates user           │   │    │
│         │     │  │ │                                        │   │    │
│         │     │  │ 💥 Step 4: Store token + redirect         │   │    │
│         │     │  │ │  ⚠️ FLOW BREAKS HERE                   │   │    │
│         │     │  │ │  Token received but never stored        │   │    │
│         │     │  │ │  No redirect after registration         │   │    │
│         │     │  │ │                                        │   │    │
│         │     │  │ ⏳ Step 5-10: Cannot proceed              │   │    │
│         │     │  │                                          │   │    │
│         │     │  │ Flow Score: 6.0/10                        │   │    │
│         │     │  └──────────────────────────────────────────┘   │    │
│         │     │                                                  │    │
│         │     │  ┌── Generated Test Scenarios ──────────────┐   │    │
│         │     │  │ 24 scenarios │ ✅ 18 would pass │ ❌ 6 fail│   │    │
│         │     │  │                                          │   │    │
│         │     │  │ R001: User Registration                  │   │    │
│         │     │  │  ✅ Happy: Register with valid data      │   │    │
│         │     │  │  ❌ Edge: Duplicate email register       │   │    │
│         │     │  │     → Would fail: no unique constraint   │   │    │
│         │     │  │  ✅ Negative: SQL injection in email     │   │    │
│         │     │  │     → Would pass: Pydantic validates     │   │    │
│         │     │  └──────────────────────────────────────────┘   │    │
│         │     │                                                  │    │
│         │     │  ┌── Gap Analysis ──────────────────────────┐   │    │
│         │     │  │ Missing:     Role-Based Access Control    │   │    │
│         │     │  │ Partial:     Task CRUD (no Update/Delete) │   │    │
│         │     │  │ Incorrect:   Token storage (never saved)  │   │    │
│         │     │  │ Extra:       Dark mode (not required)     │   │    │
│         │     │  └──────────────────────────────────────────┘   │    │
│         │     │                                                  │    │
│         │     └──────────────────────────────────────────────────┘    │
│         │  ▶ Documentation Score (README, docstrings, API docs)      │
│         │  ▶ Accessibility Report (WCAG, violations)                 │
│         │  ▶ Dependency Health (vulnerabilities, freshness)           │
│         │  ▶ Originality Analysis (boilerplate %, tutorial signals)   │
│         │  ▶ Learning Path (personalized 2-week plan)                │
│         │  ▶ Project Structure (file stats, frameworks, checklist)    │
│         │                                                            │
│         │  [📥 JSON] [📄 PDF] [📋 Copy Summary] [🔄 New Review]    │
└─────────┴────────────────────────────────────────────────────────────┘
```

### Screen 4: Batch Review

```
┌──────────────────────────────────────────────────────────────────────┐
│ Sidebar │  Batch Code Review                                         │
│         │                                                            │
│         │  ┌─ Upload Multiple Zips ─────────────────────────────┐    │
│         │  │  ☁️ Drop multiple student zip files here            │    │
│         │  └────────────────────────────────────────────────────┘    │
│         │                                                            │
│         │  ┌─ Students ─────────────────────────────────────────┐    │
│         │  │  1. alice_project.zip     Name: [Alice_____] [✕]   │    │
│         │  │  2. bob_project.zip       Name: [Bob_______] [✕]   │    │
│         │  │  3. charlie_project.zip   Name: [Charlie___] [✕]   │    │
│         │  └────────────────────────────────────────────────────┘    │
│         │                                                            │
│         │  Profile: [Bootcamp Standard ▾]  Rubric: [None ▾]         │
│         │  Problem Statement: [________________________]             │
│         │                                                            │
│         │         [ 🚀 Start Batch Review ]                          │
│         │                                                            │
│         │  ─── After completion ───                                  │
│         │                                                            │
│         │  ┌─ Comparison Matrix ────────────────────────────────┐    │
│         │  │                                                    │    │
│         │  │  Student    Overall  React  FastAPI  Sec  Test  Gr │    │
│         │  │  ─────────────────────────────────────────────────  │    │
│         │  │  Alice       8.2    8.5    7.8     8.0  7.5   A   │    │
│         │  │  Bob         6.1    7.0    5.2     4.5  3.0   B   │    │
│         │  │  Charlie     4.3    5.0    3.5     3.0  2.0   D   │    │
│         │  │  ─────────────────────────────────────────────────  │    │
│         │  │  Average     6.2    6.8    5.5     5.2  4.2       │    │
│         │  │  Median      6.1    7.0    5.2     4.5  3.0       │    │
│         │  │                                                    │    │
│         │  └────────────────────────────────────────────────────┘    │
│         │                                                            │
│         │  ┌─ Common Issues (across class) ─────────────────────┐    │
│         │  │  🔴 No Error Boundary          3/3 students (100%) │    │
│         │  │  🔴 No tests                   2/3 students (67%)  │    │
│         │  │  🟡 No loading states          3/3 students (100%) │    │
│         │  └────────────────────────────────────────────────────┘    │
│         │                                                            │
│         │  [📥 Export CSV]  [📄 Export All Reports]                  │
└─────────┴────────────────────────────────────────────────────────────┘
```

### Screen 5: History & Progress

```
┌──────────────────────────────────────────────────────────────────────┐
│ Sidebar │  Review History                                            │
│         │                                                            │
│         │  Search: [____________]  Filter: [All Projects ▾]          │
│         │                                                            │
│         │  ┌─ Past Reviews ─────────────────────────────────────┐    │
│         │  │                                                    │    │
│         │  │  📝 todo-app v3        8.2 (A)     Mar 15, 2026   │    │
│         │  │  📝 todo-app v2        7.1 (B)     Mar 08, 2026   │    │
│         │  │  📝 todo-app v1        5.5 (C)     Mar 01, 2026   │    │
│         │  │  📝 ecommerce v1       6.3 (B)     Feb 20, 2026   │    │
│         │  │                                                    │    │
│         │  └────────────────────────────────────────────────────┘    │
│         │                                                            │
│         │  ┌─ Progress: todo-app ───────────────────────────────┐    │
│         │  │                                                    │    │
│         │  │  Score                                             │    │
│         │  │  10 │                        ╭──● v3 (8.2)        │    │
│         │  │   8 │              ╭──●      │                    │    │
│         │  │   6 │  ╭──●       v2 (7.1)                        │    │
│         │  │   4 │  v1 (5.5)                                   │    │
│         │  │     └──────────────────────                        │    │
│         │  │       v1       v2       v3                         │    │
│         │  │                                                    │    │
│         │  └────────────────────────────────────────────────────┘    │
│         │                                                            │
│         │  ┌─ Version Diff (v2 → v3) ──────────────────────────┐    │
│         │  │  ✅ Resolved:  Error Boundary added (+2.0)        │    │
│         │  │  ✅ Resolved:  Added Pydantic models (+1.5)       │    │
│         │  │  🆕 New Issue: Unused dependency detected          │    │
│         │  │  🔴 Persists:  No tests for auth endpoints         │    │
│         │  └────────────────────────────────────────────────────┘    │
└─────────┴────────────────────────────────────────────────────────────┘
```

### Screen 6: Profile & Rubric Management

```
┌──────────────────────────────────────────────────────────────────────┐
│ Sidebar │  Review Profiles                                           │
│         │                                                            │
│         │  ┌─ Built-in Profiles ────────────────────────────────┐    │
│         │  │  🟢 Beginner Friendly    Lenient       [View]      │    │
│         │  │  🟡 Bootcamp Standard    Moderate      [View]      │    │
│         │  │  🔴 Production Ready     Strict        [View]      │    │
│         │  │  🔴 Interview Prep       Strict        [View]      │    │
│         │  │  🟢 Hackathon            Lenient       [View]      │    │
│         │  │  🔴 Enterprise           Very Strict   [View]      │    │
│         │  └────────────────────────────────────────────────────┘    │
│         │                                                            │
│         │  ┌─ Custom Profiles ──────────────────────────────────┐    │
│         │  │  My React Course Profile  [Edit] [Delete]          │    │
│         │  │                                                    │    │
│         │  │  [+ Create New Profile]                            │    │
│         │  └────────────────────────────────────────────────────┘    │
│         │                                                            │
│         │  ┌─ Profile Editor ───────────────────────────────────┐    │
│         │  │                                                    │    │
│         │  │  Name: [My React Course________]                   │    │
│         │  │  Strictness: [Moderate ▾]                          │    │
│         │  │  LLM Tone: [Encouraging and constructive]          │    │
│         │  │                                                    │    │
│         │  │  Agents:                                           │    │
│         │  │  ☑ React Evaluator      ☑ Security Scanner        │    │
│         │  │  ☑ FastAPI Evaluator    ☑ Performance Profiler     │    │
│         │  │  ☑ Code Smell Detector  ☐ Plagiarism Detector      │    │
│         │  │  ☑ Test Coverage        ☐ Dependency Auditor       │    │
│         │  │  ☑ Accessibility        ☑ Documentation            │    │
│         │  │                                                    │    │
│         │  │  Scoring Weights:                                  │    │
│         │  │  Code Quality    ████████░░░░ 20%  [slider]       │    │
│         │  │  Security        ██████░░░░░░ 15%  [slider]       │    │
│         │  │  Testing         ████████████ 25%  [slider]       │    │
│         │  │  Performance     ████░░░░░░░░ 10%  [slider]       │    │
│         │  │  ...                                               │    │
│         │  │                                                    │    │
│         │  │  [Save Profile]                                    │    │
│         │  └────────────────────────────────────────────────────┘    │
│         │                                                            │
│         │  ─── Rubrics ───                                           │
│         │                                                            │
│         │  ┌─ Rubric Editor ────────────────────────────────────┐    │
│         │  │                                                    │    │
│         │  │  Name: [React Fullstack Rubric____]                │    │
│         │  │                                                    │    │
│         │  │  Category       Weight   Min Expectations          │    │
│         │  │  ──────────────────────────────────────────────    │    │
│         │  │  Security        25%     Auth, no hardcoded keys   │    │
│         │  │  Code Quality    20%     No god components         │    │
│         │  │  Testing         20%     1 test per endpoint       │    │
│         │  │  API Design      15%     RESTful, proper statuses  │    │
│         │  │  Documentation   10%     README with setup         │    │
│         │  │  Accessibility   10%     All images have alt       │    │
│         │  │                                                    │    │
│         │  │  [+ Add Category]  [Save Rubric]                   │    │
│         │  └────────────────────────────────────────────────────┘    │
└─────────┴────────────────────────────────────────────────────────────┘
```

### Overlay: AI Chat Panel

```
┌─── Report Dashboard ──────────────┬─── AI Chat ────────────────────┐
│                                   │                                 │
│  (report content)                 │  🤖 Ask about your review      │
│                                   │                                 │
│                                   │  ┌─ Suggested ───────────────┐ │
│                                   │  │ "How do I add an Error    │ │
│                                   │  │  Boundary?"               │ │
│                                   │  │ "Explain finding #3"      │ │
│                                   │  │ "What should I fix first?"│ │
│                                   │  └───────────────────────────┘ │
│                                   │                                 │
│                                   │  You: How do I fix the SQL     │
│                                   │       injection issue?          │
│                                   │                                 │
│                                   │  AI: In your orders.py line    │
│                                   │      34, you're using an       │
│                                   │      f-string directly in the  │
│                                   │      SQL query. Here's how     │
│                                   │      to fix it:                │
│                                   │                                 │
│                                   │      ```python                 │
│                                   │      # Before (vulnerable)     │
│                                   │      db.execute(f"SELECT *     │
│                                   │        FROM orders WHERE       │
│                                   │        id = {order_id}")       │
│                                   │                                 │
│                                   │      # After (safe)            │
│                                   │      db.execute(               │
│                                   │        "SELECT * FROM orders   │
│                                   │         WHERE id = :id",       │
│                                   │        {"id": order_id}        │
│                                   │      )                         │
│                                   │      ```                       │
│                                   │                                 │
│                                   │  [____________________] [Send] │
└───────────────────────────────────┴─────────────────────────────────┘
```

### Overlay: Code Viewer Panel

```
┌─── Report Dashboard ──────────────┬─── Code Viewer ────────────────┐
│                                   │                                 │
│  (report content with             │  📄 backend/services/orders.py  │
│   finding highlighted)            │  [◀ Prev Issue] [Next Issue ▶]  │
│                                   │  ─────────────────────────────  │
│                                   │  30 │ async def get_order(      │
│                                   │  31 │     order_id: str,        │
│                                   │  32 │     db: Session            │
│                                   │  33 │ ):                         │
│                                   │ 🔴34│     result = db.execute(  │
│                                   │     │       f"SELECT * FROM     │
│                                   │     │       orders WHERE        │
│                                   │     │       id = {order_id}"    │
│                                   │     │     )                      │
│                                   │     │                            │
│                                   │     │ ┌─ Finding ─────────────┐ │
│                                   │     │ │ 🔴 SQL Injection      │ │
│                                   │     │ │ Raw SQL with f-string │ │
│                                   │     │ │ formatting. Use       │ │
│                                   │     │ │ parameterized queries │ │
│                                   │     │ └───────────────────────┘ │
│                                   │  35 │     return result.first() │
│                                   │  36 │                            │
│                                   │                                 │
│                                   │  [Close]                        │
└───────────────────────────────────┴─────────────────────────────────┘
```

---

## 9. Component Specifications

### 9.1 DropZone

| Prop | Type | Description |
|---|---|---|
| `mode` | `"combined" \| "separate"` | Single or dual zones |
| `onFileDrop` | `(field, file) => void` | Callback on accept |
| `multiple` | `boolean` | Allow multiple (for batch) |
| `maxSize` | `number` | Max bytes (default 50MB) |

Behaviors:
- react-dropzone with `accept: { "application/zip": [".zip"] }`
- Drag states: idle (dashed gray) → active (dashed blue) → rejected (dashed red)
- Validates zip magic bytes (PK header) as extra check
- Separate mode: two side-by-side zones labeled "Frontend" / "Backend"
- Batch mode: single zone accepting multiple files

### 9.2 AgentTimeline

Groups agents by phase. Shows parallel indicator for Phase 2. Each AgentStep receives:
- `agent`: Agent metadata from registry
- `status`: pending | running | done | error | skipped
- `message`: Latest progress message
- `score`: Partial score if available (shown as badge when done)

Phase 2 agents render with a "parallel" visual indicator (branching lines or side-by-side layout).

Status styling:
- **pending**: Gray circle, muted text
- **running**: Blue circle + animated pulse, bold text, spinner icon
- **done**: Green circle + checkmark, message + score badge
- **error**: Red circle + X, error message
- **skipped**: Gray circle + dash, "Skipped" label

### 9.3 RadialGauge

Recharts `RadialBarChart` with animated fill.
- Inner label: score (large) + "/10" (small)
- Color: `scoreColor(score)` — red 0-4, amber 4-7, green 7-10
- Letter grade badge below
- Animated on mount (0 → score over 800ms)

### 9.4 FindingsPanel

Three-tab interface with count badges:
- **Critical** (red tab) — `type === "negative"`
- **Suggestions** (amber tab) — `type === "suggestion"`
- **Strengths** (green tab) — `type === "positive"`

Each FindingCard shows:
- Severity icon (🔴 / 💡 / ✅)
- Area badge (colored chip: "Security", "Error Handling", etc.)
- Detail text
- `[View Code →]` link if file reference exists → opens CodeViewerPanel
- `[Show Fix ▾]` expandable → shows FindingDiffView with before/after

### 9.5 IntegrationMap (EndpointMap)

Two-column layout with connecting indicators:

```
Frontend API Calls           Backend Endpoints
─────────────────           ─────────────────
GET  /api/tasks    ←—✅—→  GET  /api/tasks
POST /api/tasks    ←—✅—→  POST /api/tasks
GET  /api/users    ←—❌     (no match)
                    ⚠️—→   DELETE /api/tasks/:id (unused)
```

Colors: green = matched, red = FE with no BE, amber = BE with no FE consumer.
LLM contract notes rendered below as callout cards.

### 9.6 RequirementsTable

| Requirement | Status | Evidence |
|---|---|---|
| User auth | ✅ Met | JWT in auth.py |
| CRUD | ⚠️ Partial | No Update/Delete |
| Error handling | ❌ Missing | No global handler |

Completeness bar at top. Missing features as red chips below.

### 9.7 ArchitectureDiagram

- Fetches Mermaid code from `GET /review/{id}/diagram/{type}`
- DiagramTypeSelector tabs: Component Tree | API Flow | Data Model | Full Architecture
- MermaidRenderer initializes mermaid.js and renders SVG
- Zoomable/pannable container
- Download as SVG / PNG

### 9.8 CodeViewerPanel

- SlidePanel from right (50% width)
- Monaco Editor in read-only mode
- GutterAnnotations overlay markers at finding lines
- FindingTooltip on hover/click
- IssueNavigator: prev/next buttons cycling through annotations
- File path + line count in header

### 9.9 ChatPanel

- SlidePanel from right (40% width) or bottom drawer on mobile
- ChatMessageList with auto-scroll
- User messages right-aligned, AI messages left-aligned
- ChatCodeBlock with syntax highlighting for code in responses
- SuggestedQuestions chips at top (generated from critical findings)
- Streaming indicator (pulsing dots) while Ollama responds

### 9.10 ComparisonTable (Batch)

- DataTable with sortable columns
- Each student row is clickable → navigates to their full report
- Color-coded cells (red < 5, amber 5-7, green > 7)
- Footer row with class averages
- Export as CSV button

### 9.11 ProgressChart (History)

- Recharts LineChart with score on Y-axis, version on X-axis
- Multiple lines for each category (toggleable legend)
- Hover tooltip showing all scores for that version
- Click a point → navigates to that version's full report

### 9.12 LearningPathPanel

- Rendered in report accordion
- WeekPlan sections (Week 1, Week 2)
- Each LearningItem card:
  - Topic title (bold)
  - "Why it matters" paragraph
  - Practice exercise in a callout box
  - Time estimate badge (e.g., "~3 hrs")
- SkillGapRadar: Recharts RadarChart with skill areas on axes

---

## 10. Feature Specifications (9 Features)

### F1 — Interactive Code Viewer with Annotated Findings

- **Trigger:** Click `[View Code →]` on any finding with file reference
- **Loads:** File content via `GET /review/{id}/file/{path}`
- **Displays:** Monaco Editor (read-only) with gutter annotations
- **Navigation:** Prev/Next issue buttons, keyboard shortcuts (J/K)
- **Annotations:** Red markers for critical, amber for suggestions, green for strengths
- **Tooltip:** Hover on marker shows finding detail + fix suggestion

### F2 — Scoring Rubric Builder

- **Where:** Profiles page → Rubric Editor
- **Create:** Define categories with name, weight (%), and minimum expectations (text)
- **Weights** must sum to 100% (enforced with validation + auto-balance option)
- **Usage:** Select rubric during upload → Report Generator uses rubric weights instead of defaults
- **Report:** Shows "Rubric Alignment" section comparing actual vs expected per category
- **Storage:** SQLite rubrics table

### F3 — Diff View / Before-After Fix Suggestions

- **Trigger:** Click `[Show Fix ▾]` on a finding
- **Generates:** LLM creates corrected version of the problematic code snippet
- **Displays:** react-diff-viewer with split view (red = current, green = suggested)
- **Cache:** Fix suggestions cached per finding to avoid repeated LLM calls
- **Backend:** `POST /review/{id}/fix-suggestion` with finding details → Ollama generates fix

### F4 — Batch Review Mode

- **Upload:** Multiple zips with student name fields
- **Execution:** Parallel LangGraph pipelines (configurable concurrency limit)
- **SSE:** Tagged events with `student_index` for per-student progress tracking
- **Comparison:** Auto-generated after all students complete
- **Stats:** Mean, median, std deviation per category + percentile ranks
- **Common Issues:** Issues appearing in > 50% of submissions flagged as systemic
- **Export:** Full comparison CSV + individual report JSONs in a zip

### F5 — Learning Path Generator

- **Agent:** Runs as sub-process of Report Generator
- **Input:** All agent findings + inferred skill level
- **Output:** 2-week prioritized plan with daily topics, exercises, and time estimates
- **Display:** Accordion in report + SkillGapRadar chart
- **LLM Prompt:** Structured to produce JSON with week/day/topic/exercise/time fields

### F6 — Re-Review & Progress Tracking

- **Auto-detect:** If same `project_id` + `student_name` exists, auto-increment version
- **History page:** Lists all reviews with filter/search
- **Progress chart:** Score trends across versions
- **Version diff:** Side-by-side showing resolved, persistent, and new issues
- **Storage:** SQLite reviews table with version column

### F7 — AI Chat Follow-Up

- **Context:** Full report JSON + code snippets for referenced findings injected as system prompt
- **Streaming:** SSE from `POST /review/{id}/chat`
- **History:** Chat messages stored in SQLite, persisted per session
- **Suggested questions:** Auto-generated from top 3 critical findings
- **Code blocks:** Syntax-highlighted in chat responses
- **Scope guard:** If student asks off-topic, AI redirects to review findings

### F8 — Architecture Diagram Auto-Generation

- **Types:** Component tree, API flow, Data model, Dependency graph, Full architecture
- **Generation:** Agent parses imports + JSX + decorators → generates Mermaid code via Ollama
- **Display:** MermaidRenderer component with type selector tabs
- **Interactive:** Zoomable, pannable, downloadable as SVG/PNG
- **Fallback:** If Mermaid generation fails, show raw code with manual edit option

### F9 — Configurable Review Profiles

- **6 Built-in profiles** seeded in SQLite (Beginner, Bootcamp, Production, Interview, Hackathon, Enterprise)
- **Custom profiles:** Create/edit/delete via ProfileEditor
- **Config fields:** Name, description, strictness level, LLM tone, agent toggles, scoring weights
- **Effect on pipeline:**
  - Agent toggles → skip disabled agents (produce `{ skipped: true }`)
  - Scoring weights → Report Generator uses profile weights
  - LLM tone → Injected into all agent system prompts
  - Strictness → Adjusts thresholds (e.g., "lenient" requires 8+ console.logs to flag, "strict" flags at 3+)

---

## 11. Styling & Theming

### CSS Variables (Dark Theme — Default)

```css
:root {
  --bg-primary: #0f1117;
  --bg-secondary: #1a1d27;
  --bg-card: #222633;
  --bg-card-hover: #2a2e3d;
  --bg-sidebar: #161822;

  --text-primary: #e8eaed;
  --text-secondary: #9aa0ac;
  --text-muted: #5f6578;

  --accent-blue: #4f8ff7;
  --accent-green: #34d399;
  --accent-red: #f87171;
  --accent-amber: #fbbf24;
  --accent-purple: #a78bfa;
  --accent-cyan: #22d3ee;

  --border: #2d3140;
  --border-active: #4f8ff7;
  --border-hover: #3d4155;

  --score-low: #f87171;       /* 0-4 */
  --score-mid: #fbbf24;       /* 4-7 */
  --score-high: #34d399;      /* 7-10 */

  --severity-critical: #ef4444;
  --severity-high: #f97316;
  --severity-medium: #eab308;
  --severity-low: #6b7280;

  --radius-sm: 6px;
  --radius: 12px;
  --radius-lg: 16px;
  --shadow: 0 4px 24px rgba(0,0,0,0.3);
  --shadow-lg: 0 8px 40px rgba(0,0,0,0.5);

  --sidebar-width: 240px;
  --panel-width: 50%;
}
```

### Light Theme Override

```css
[data-theme="light"] {
  --bg-primary: #f8f9fc;
  --bg-secondary: #ffffff;
  --bg-card: #ffffff;
  --bg-card-hover: #f3f4f6;
  --bg-sidebar: #f1f3f8;
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --text-muted: #9ca3af;
  --border: #e5e7eb;
  --shadow: 0 4px 24px rgba(0,0,0,0.08);
}
```

### Typography

```
Font: Inter, system-ui, -apple-system, sans-serif
Mono: JetBrains Mono, Fira Code, monospace

Scale:
  xs:  12px / 1.4
  sm:  13px / 1.5
  base: 14px / 1.6
  md:  16px / 1.5
  lg:  20px / 1.4
  xl:  28px / 1.3
  2xl: 36px / 1.2
```

### Design Tokens

- Cards: `bg-card`, `radius`, `shadow`, 1px `border`
- Inner padding: 16-20px
- Card gap: 20-24px
- Section gap: 32px
- Sidebar: fixed left, `sidebar-width`, `bg-sidebar`
- Slide panels: `panel-width` from right, `shadow-lg`, z-index 50

---

## 12. Responsive Layout Grid

### Desktop (> 1280px)

```
┌─ Sidebar ─┬─────────────────────────────────────────────────┐
│  240px     │  Main Content Area                              │
│  fixed     │  ┌──────────────┬──────────────────────────┐   │
│            │  │  Score Card   │  Category Scores Grid     │   │
│            │  └──────────────┴──────────────────────────┘   │
│            │  ┌──────────────────────────────────────────┐   │
│            │  │  Priority Actions (full width)            │   │
│            │  └──────────────────────────────────────────┘   │
│            │  ┌──────────────────────────────────────────┐   │
│            │  │  Executive Summary (full width)           │   │
│            │  └──────────────────────────────────────────┘   │
│            │  ┌──────────────────────────────────────────┐   │
│            │  │  Findings Panel (full width, tabbed)      │   │
│            │  └──────────────────────────────────────────┘   │
│            │  ┌──────────────┬──────────────────────────┐   │
│            │  │ Security     │  Performance              │   │
│            │  └──────────────┴──────────────────────────┘   │
│            │  ┌──────────────┬──────────────────────────┐   │
│            │  │ Code Quality │  Test Coverage            │   │
│            │  └──────────────┴──────────────────────────┘   │
│            │  ┌──────────────────────────────────────────┐   │
│            │  │  Integration Map (full width)             │   │
│            │  └──────────────────────────────────────────┘   │
│            │  ┌──────────────────────────────────────────┐   │
│            │  │  Architecture Diagram (full width)        │   │
│            │  └──────────────────────────────────────────┘   │
│            │  ... remaining accordion sections              │
└────────────┴─────────────────────────────────────────────────┘
```

### Tablet (768-1280px)

- Sidebar collapses to icon-only (64px) with tooltip labels
- Score + categories stack vertically
- Report sections single column
- Slide panels take 70% width

### Mobile (< 768px)

- Sidebar becomes bottom navigation bar (5 icons)
- Everything single column
- Slide panels become full-screen overlays
- RadialGauge scales down (200px → 150px)
- Findings tabs become horizontal scrollable strip
- Integration map becomes vertical list
- Chat becomes bottom drawer (70% height)

---

## 13. Animations & Micro-interactions

| Element | Animation | Library | Duration |
|---|---|---|---|
| Page transitions | Fade + slide | Framer Motion | 200ms |
| Drop zone dragover | Border pulse, bg opacity | CSS transition | 150ms |
| Agent step status change | Slide-in + fade | Framer Motion | 300ms |
| Phase 2 parallel indicator | Staggered fan-out | Framer Motion | 400ms |
| Score gauge fill | Count-up spiral | Recharts animated | 800ms |
| Grade badge | Pop-in scale | Framer Motion spring | 500ms |
| Finding cards | Staggered fade-in on tab switch | Framer Motion | 50ms stagger |
| Code viewer slide | Slide from right | Framer Motion | 250ms |
| Chat panel slide | Slide from right | Framer Motion | 250ms |
| Chat message | Fade-in + slight slide-up | Framer Motion | 200ms |
| Chat streaming | Token-by-token append | React state | per token |
| Diff view expand | Height animate + fade | Framer Motion | 300ms |
| Mermaid diagram | Fade-in after render | CSS | 200ms |
| Report accordions | Height + opacity | Framer Motion | 250ms |
| Toast notification | Slide from top-right | Sonner | 300ms in / 200ms out |
| Button hover | Scale 1.02 + shadow | CSS | 150ms |
| Card hover | Border color + shadow | CSS | 150ms |
| Progress chart points | Scale pop on hover | Recharts | 150ms |
| Comparison table rows | Staggered fade | Framer Motion | 30ms stagger |
| Sidebar collapse | Width animate | CSS | 200ms |

---

## 14. Review Profiles & Rubric System

### Built-in Profiles

| Profile | Strictness | Agents Enabled | LLM Tone | Use Case |
|---|---|---|---|---|
| **Beginner Friendly** | Lenient | Core 7 only (no complexity, plagiarism, deps) | Encouraging, supportive | First-time students |
| **Bootcamp Standard** | Moderate | All 16 | Constructive, direct | Bootcamp assignments |
| **Production Ready** | Strict | All 16, strict thresholds | Professional, thorough | Pre-deployment review |
| **Interview Prep** | Strict | All 16, competitive scoring | Evaluative, like a senior interviewer | Interview practice |
| **Hackathon** | Lenient | Skip plagiarism, docs, a11y | Enthusiastic, practical | Hackathon judging |
| **Enterprise** | Very Strict | All 16 + extra checks (CI/CD, logging, monitoring) | Formal, compliance-focused | Enterprise audits |

### Strictness Thresholds

| Check | Lenient | Moderate | Strict | Very Strict |
|---|---|---|---|---|
| console.log flagging | > 10 | > 5 | > 3 | > 0 |
| `any` type flagging | > 8 | > 3 | > 1 | > 0 |
| Function max lines | 80 | 50 | 30 | 25 |
| Component max lines | 500 | 300 | 200 | 150 |
| Cyclomatic complexity danger | > 25 | > 15 | > 10 | > 8 |
| Min test file ratio | 0.1 | 0.3 | 0.5 | 0.7 |
| Min docstring coverage | 10% | 30% | 60% | 80% |

### Default Scoring Weights

| Category | Default Weight | What Feeds It |
|---|---|---|
| Code Quality | 15% | Code Smell Detector + Complexity Analyzer |
| Security | 15% | Security Scanner |
| Architecture | 10% | Structure Analyzer + Integration Analyzer |
| Frontend Quality | 10% | React Evaluator |
| Backend Quality | 10% | FastAPI Evaluator |
| Testing | 10% | Test Coverage Analyzer |
| Performance | 10% | Performance Profiler |
| Documentation | 5% | Documentation Scorer |
| Accessibility | 5% | Accessibility Checker |
| Originality | 5% | Plagiarism Detector |
| Requirements | 5% | Requirements Validator (0% if no problem statement) |

When rubric is applied, these weights are overridden by rubric category weights.

---

## 15. Backend Implementation Details (All 16 Agents)

### Agent 1 — Extract & Classify

```
Input:  Zip file(s) on disk
Output: file_tree[], frontend_files{}, backend_files{}, config_files{}

Logic:
  1. Validate zip before extraction (ZIP bomb protection):
     - Check compressed-to-uncompressed ratio (abort if > 100:1)
     - Limit total uncompressed size to 500MB
     - Limit total file count to 2000 files
     - Reject paths with ../ (path traversal)
  2. zipfile.extractall() to temp directory (unique per session_id)
  3. Register temp dir for cleanup: deleted after report is generated or session expires (24h TTL)
  4. Walk all files, build file_tree with path, size, extension
  5. Skip patterns: node_modules, __pycache__, .git, dist, build, venv, .lock, binaries
  6. Classify by extension:
     - Frontend: .tsx, .jsx, .ts, .js, .css, .scss, .html
     - Backend:  .py
     - Config:   package.json, requirements.txt, tsconfig, dockerfile, etc.
  5. Read file contents (utf-8, errors=ignore)

LLM: None (pure extraction)
```

### Agent 2 — Structure Analyzer

```
Input:  Classified files + config files
Output: structure_analysis with frameworks, dependencies, folder structure checks

Logic:
  1. Parse package.json → extract deps, detect FE frameworks
  2. Parse requirements.txt → extract deps, detect BE frameworks
  3. Check folder conventions:
     FE: has_components, has_pages, has_hooks, has_services, has_types, has_utils
     BE: has_routers, has_models, has_schemas, has_services, has_tests, has_migrations
  4. Count files + lines per category
  5. Detect build tools (Vite, Webpack, etc.)

LLM: None (pure parsing)
```

### Agent 3 — React Evaluator

```
Input:  frontend_files{}
Output: react_evaluation with score, sub_scores, findings, llm_analysis, stats

Static Checks (regex patterns):
  - Hook usage: useState, useEffect, useCallback, useMemo, useRef
  - Custom hooks: function/const use[A-Z]
  - Error boundaries: componentDidCatch, ErrorBoundary
  - Prop types: interface/type \w+Props
  - Memoization: React.memo, memo()
  - Lazy loading: React.lazy, lazy()
  - Code splitting: Suspense
  - Console logs count
  - any type count
  - Inline styles count
  - API calls: fetch, axios, useQuery, useMutation
  - Loading/error states
  - Key props in JSX
  - useEffect cleanup returns
  - Fragment usage

LLM Deep Analysis:
  - Send top 8 key files (prioritize app, index, main, layout, page)
  - Prompt: component quality, state management, performance, security, violations, strengths, suggestions
  - Parse JSON response

Scoring: Base 5 + deltas from static checks (capped 0-10)
```

### Agent 4 — FastAPI Evaluator

```
Input:  backend_files{}
Output: fastapi_evaluation with score, sub_scores, findings, llm_analysis, stats

Static Checks:
  - Endpoint decorators: @app|router.(get|post|put|patch|delete)
  - Pydantic models: class \w+(BaseModel)
  - Dependency injection: Depends()
  - HTTPException usage
  - try/except blocks
  - async vs sync handlers
  - Raw SQL detection (f-strings in execute)
  - ORM usage (session.add/delete/commit)
  - CORS middleware
  - Auth patterns (OAuth, JWT, Bearer, verify_token)
  - Environment variables (os.getenv, Settings)
  - Logging
  - Type hints
  - Middleware
  - Rate limiting
  - Test files
  - Docstrings

LLM Deep Analysis:
  - Send top 8 files by size
  - Prompt: API design, security, performance, vulnerabilities, violations, strengths, suggestions
  - Parse JSON response

Scoring: Base 5 + deltas (capped 0-10)
```

### Agent 5 — Security Scanner

```
Input:  All files (FE + BE + config)
Output: security_scan with severity_counts, findings[], owasp_coverage, security_score

Static Checks:
  - Hardcoded secrets: regex for sk-, ghp_, AKIA, password=, secret=, api_key=
  - .env.example with real values
  - SQL injection: f-strings in .execute()
  - XSS: dangerouslySetInnerHTML without sanitizer
  - CSRF: presence/absence of CSRF protection
  - CORS: allow_origins=["*"]
  - Unprotected routes: endpoints without Depends(get_current_user)
  - Insecure deserialization: pickle.loads, eval(), exec()
  - Path traversal: ../ in file operations
  - Insecure HTTP: http:// URLs
  - JWT issues: no expiry, weak algorithm
  - Exposed error details in responses
  - Missing rate limiting on auth endpoints
  - Sensitive data in logs

LLM Deep Analysis:
  - Send auth flow code + data input handlers
  - Prompt: Taint analysis (user input → database trace)
  - Prompt: Privilege escalation paths
  - Prompt: OWASP Top 10 coverage assessment

OWASP Mapping: Each finding tagged with OWASP category (A01-A10)
Scoring: 10 - (critical×2 + high×1.5 + medium×0.5 + low×0.1), capped 0-10
```

### Agent 6 — Performance Profiler

```
Input:  frontend_files{}, backend_files{}
Output: performance_profile with frontend_perf, backend_perf, performance_score

Frontend Checks:
  - Heavy imports: moment.js, lodash full import (import _ from 'lodash')
  - Re-render traps: new object/array in JSX props, inline object props
  - Missing dependency arrays in useEffect
  - Large lists without virtualization (.map() > 50 items, no react-window)
  - Missing image lazy loading
  - No code splitting (absence of React.lazy)
  - N+1 API calls: fetch inside .map(), useEffect per item
  - CSS-in-JS in hot paths
  - Bundle duplication hints (multiple similar imports)

Backend Checks:
  - Sync I/O in async handlers (open(), read() without aiofiles)
  - N+1 queries: ORM query in a loop
  - Missing connection pool config
  - No pagination (returning all rows)
  - Missing caching (no Redis, no cache headers)
  - Large file reads without streaming
  - Heavy imports at module level
  - Missing async for DB operations

LLM Analysis:
  - Send key files + identified bottleneck patterns
  - Prompt: Performance review, hot path identification, optimization priorities

Scoring: Base 5 + deltas (capped 0-10)
```

### Agent 7 — Code Smell Detector

```
Input:  All source files
Output: code_smells with smells[], smell_density, code_quality_score

Detections (all via static analysis):
  - God Component: React component > 300 lines or > 10 useState
  - God Function: any function > 50 lines
  - God File: any file > 500 lines
  - Deep Nesting: indentation > 4 levels
  - Duplicate Code: Levenshtein similarity > 80% between blocks
  - Dead Code: exported but never imported (cross-file analysis)
  - Magic Numbers: numeric literals in logic (not in constants)
  - Prop Drilling: props passed > 3 levels unchanged
  - Mixed Concerns: API calls in component render (no service layer)
  - Inconsistent Naming: camelCase + snake_case in same language
  - Long Parameter Lists: functions with > 5 params
  - Empty Catch Blocks: catch(e) {}
  - TODO/FIXME/HACK markers
  - Console pollution (console.log count)
  - Excessive Comments (restate code, not explain why)

LLM Enhancement:
  - Send top smelly files
  - Prompt: Architectural smells, coupling, circular deps, missing abstractions
  - Prompt: Refactoring suggestions with before/after

Scoring: 10 - (smell_density × 1.5), capped 0-10
```

### Agent 8 — Test Coverage Analyzer

```
Input:  All files (source + test files)
Output: test_analysis with test_file_ratio, test_types, untested_critical_paths, test_quality, testing_score

Logic:
  1. Identify test files: files matching *test*, *spec*, test_*, *_test.*
  2. Identify source files: everything else
  3. Map source → test: check for corresponding test file per source module
  4. Parse test content:
     - Count test functions: test_, it(, describe(
     - Classify: unit (no imports from other modules), integration (DB/API), e2e (browser/client)
     - Count assertions per test
     - Detect mock usage
     - Detect snapshot tests
  5. Critical path gap detection:
     - Backend: endpoints without test files
     - Frontend: components without test files
     - Auth flows without tests
     - Data mutation operations without tests

LLM Analysis:
  - Send test files + corresponding source files
  - Prompt: "Are these tests testing meaningful behavior or implementation details?"
  - Prompt: "What critical test cases are missing?"

Scoring: Composite of test_file_ratio, assertion density, critical gap count (capped 0-10)
```

### Agent 9 — Dependency Auditor

```
Input:  config_files{} (package.json, requirements.txt)
Output: dependency_audit with frontend_deps, backend_deps, concerns[], dependency_score

Logic:
  1. Parse package.json: count production vs dev deps
  2. Parse requirements.txt: parse package names
  3. Check for known issues (via Ollama knowledge):
     - Abandoned: moment.js, request, etc.
     - Deprecated: python-jose → PyJWT, etc.
     - Duplicate functionality: axios + fetch wrapper, lodash + underscore
     - License concerns: GPL in MIT projects (parse license field)
     - Version pinning: exact vs range
     - Excessive deps for project size
  4. Count total deps, flag if > 30 production deps

LLM Analysis:
  - Send full dependency lists
  - Prompt: "Which are outdated, abandoned, have known CVEs? Suggest lighter alternatives."

Scoring: 10 - (critical_concerns × 2 + medium × 0.5), capped 0-10
```

### Agent 10 — Accessibility Checker

```
Input:  frontend_files{}
Output: accessibility_report with violations[], wcag_summary, accessibility_score

Static Checks:
  - <img> without alt
  - <button>/<a> without accessible text (aria-label or inner text)
  - <div onClick> without role="button" + tabIndex
  - <input> without <label> or aria-label
  - Missing skip navigation
  - Missing lang on <html>
  - Heading hierarchy violations (h1 → h3 skipping h2)
  - Focus management in modals
  - Missing aria-live for dynamic content
  - Keyboard traps (tabIndex without escape)
  - Low-contrast color values in inline styles / Tailwind

LLM Analysis:
  - Send component code
  - Prompt: "WCAG 2.1 AA compliance review"
  - Prompt: "Keyboard accessibility review"

Scoring: 10 - (critical × 2 + serious × 1 + moderate × 0.5), capped 0-10
```

### Agent 11 — Documentation Scorer

```
Input:  All files (especially README, docstrings, config)
Output: documentation_report with readme_score, docstring_coverage, documentation_score

Checks:
  README.md:
  - Exists?
  - Has project description?
  - Has setup/installation instructions?
  - Has usage examples?
  - Has API documentation?
  - Has env vars documentation?
  - Has contributing guidelines?
  - Word count, section count

  Python:
  - Count functions with vs without docstrings
  - Docstring quality (one-liner vs descriptive)

  TypeScript:
  - JSDoc/TSDoc coverage on exported functions
  - Interface documentation

  FastAPI:
  - Endpoint docstrings (visible in /docs)
  - Response model documentation

LLM Analysis:
  - Send README + key files
  - Prompt: "Could a new developer onboard from this documentation alone?"
  - Prompt: "What's missing from this README?"

Scoring: Weighted composite of readme + docstrings + API docs (capped 0-10)
```

### Agent 12 — Integration Analyzer

```
Input:  frontend_files{}, backend_files{}, results from agents 3-4
Output: integration_analysis with endpoint_map, contract_mismatches, integration_score

Logic:
  1. Extract BE endpoints: regex for @app|router.(method)("path")
  2. Extract FE API calls: regex for fetch("url"), axios.method("url")
  3. Detect base URL configuration
  4. Match FE calls ↔ BE endpoints by path + method
  5. Identify unmatched FE calls (API not found)
  6. Identify unused BE endpoints (no FE consumer)

LLM Analysis:
  - Send FE API code + BE endpoint code
  - Prompt: Endpoint coverage, data flow issues, contract mismatches, error handling gaps

Scoring: Based on match ratio + LLM findings severity (capped 0-10)
```

### Agent 13 — Functional Validation Engine (Upgraded Requirements Validator)

```
Input:  problem_statement, all files, structure_analysis, react_evaluation, fastapi_evaluation, integration_analysis
Output: functional_validation with parsed_requirements[], validation_results[], functional_score,
        test_scenarios[], traceability_matrix, completeness_score, gap_analysis

Conditional: Only runs if problem_statement is provided
Depends on: Agents 2, 3, 4, 12 (needs their outputs for cross-referencing)

This is a 5-pass deep validation pipeline, not a single LLM call.
```

#### Pass 1 — Requirement Parsing & Decomposition

```
Purpose: Break the problem statement into discrete, testable functional requirements

LLM Prompt:
  "Parse this problem statement into a structured list of functional requirements.
   For each requirement, classify it and identify what code evidence would prove it.

   PROBLEM STATEMENT:
   {problem_statement}

   Return ONLY valid JSON:
   {
     "requirements": [
       {
         "id": "R001",
         "category": "authentication|crud|ui|validation|integration|business_logic|error_handling|performance|security|data_model",
         "title": "User Registration",
         "description": "Users should be able to register with email and password",
         "acceptance_criteria": [
           "Registration form with email and password fields",
           "Email format validation",
           "Password minimum length enforcement",
           "Duplicate email prevention",
           "Success confirmation after registration"
         ],
         "requires_frontend": true,
         "requires_backend": true,
         "requires_database": true,
         "priority": "must_have|should_have|nice_to_have",
         "expected_evidence": {
           "frontend": ["registration form component", "email input", "password input", "submit handler", "validation messages"],
           "backend": ["POST /register or /signup endpoint", "email uniqueness check", "password hashing", "user creation in DB"],
           "database": ["users table or model with email and password fields"]
         }
       }
     ],
     "implicit_requirements": [
       {
         "id": "IR001",
         "title": "Error Handling",
         "description": "Not stated but expected — proper error responses for all operations"
       }
     ]
   }"

Output: parsed_requirements[] with IDs, categories, acceptance criteria, expected evidence
```

#### Pass 2 — Code Evidence Collection (Per Requirement)

```
Purpose: For each parsed requirement, search the actual codebase for implementation evidence

Logic (automated, no LLM):
  For each requirement:
    1. Search frontend_files for expected frontend evidence:
       - Component names matching requirement (e.g., "Register", "Login", "TaskForm")
       - Form elements (<input>, <form>, <button type="submit">)
       - API calls matching expected endpoints
       - Validation logic (Zod/Yup schemas, inline validation)
       - State management for the feature
       - Error/loading/success states
       - Route definitions matching the feature

    2. Search backend_files for expected backend evidence:
       - Endpoint decorators matching expected routes
       - Pydantic models matching expected request/response shapes
       - Database model fields matching expected data
       - Service functions implementing business logic
       - Validation logic in schemas/models
       - Error handling for the feature

    3. Cross-reference with integration_analysis:
       - Does the FE API call match a BE endpoint for this requirement?
       - Does the request payload shape match the Pydantic model?
       - Is the response used correctly in the frontend?

    4. Collect code snippets as evidence:
       - File path + line numbers
       - Relevant code snippets (truncated to 50 lines max per evidence)

Output per requirement:
  {
    "requirement_id": "R001",
    "frontend_evidence": [
      { "file": "src/components/Register.tsx", "lines": "15-45", "snippet": "...", "matches": ["form", "email input", "password input"] }
    ],
    "backend_evidence": [
      { "file": "backend/routers/auth.py", "lines": "20-35", "snippet": "...", "matches": ["POST /register", "password hashing"] }
    ],
    "database_evidence": [
      { "file": "backend/models/user.py", "lines": "5-15", "snippet": "...", "matches": ["User model", "email field", "password field"] }
    ],
    "integration_evidence": {
      "fe_call_found": true,
      "be_endpoint_found": true,
      "contract_match": true
    },
    "evidence_coverage": 0.85  // what % of expected evidence was found
  }
```

#### Pass 3 — Deep Functional Validation (LLM Per Requirement)

```
Purpose: For each requirement, send the collected evidence to Ollama for deep validation
         This is where we check CORRECTNESS, not just presence

LLM Prompt (per requirement, batched where possible):
  "You are validating whether this specific requirement is correctly implemented.

   REQUIREMENT:
   {requirement.title}: {requirement.description}

   ACCEPTANCE CRITERIA:
   {requirement.acceptance_criteria}

   FRONTEND CODE EVIDENCE:
   {frontend_evidence snippets}

   BACKEND CODE EVIDENCE:
   {backend_evidence snippets}

   DATABASE EVIDENCE:
   {database_evidence snippets}

   INTEGRATION STATUS:
   FE→BE call matched: {yes/no}
   Contract aligned: {yes/no}

   Evaluate EACH acceptance criterion individually. For each one, determine:
   1. Is it implemented? (yes/partially/no)
   2. Is the implementation CORRECT? (does it actually work as intended?)
   3. Are edge cases handled?
   4. Are there bugs or logic errors in the implementation?

   Return ONLY valid JSON:
   {
     "requirement_id": "R001",
     "overall_status": "met|partial|missing|incorrect",
     "criteria_results": [
       {
         "criterion": "Registration form with email and password fields",
         "status": "met|partial|missing|incorrect",
         "correctness": "correct|has_bugs|incomplete",
         "evidence_file": "src/components/Register.tsx",
         "evidence_line": 15,
         "assessment": "Form exists with both fields but lacks proper HTML5 validation attributes",
         "issues": ["Missing type='email' on email input", "No autocomplete attributes"],
         "severity": "minor|moderate|critical"
       }
     ],
     "edge_cases_handled": ["duplicate email check", "empty field validation"],
     "edge_cases_missing": ["SQL injection on email", "password strength indicator"],
     "bugs_found": [
       {
         "description": "Password is sent in plain text — not hashed before storage",
         "file": "backend/routers/auth.py",
         "line": 28,
         "severity": "critical",
         "fix": "Use bcrypt.hash() before storing password"
       }
     ],
     "functional_score": 7.5
   }"
```

#### Pass 4 — End-to-End Flow Validation

```
Purpose: Validate complete user flows that span multiple requirements
         (e.g., "register → login → create task → view tasks")

Logic:
  1. Identify user flows from requirements:
     - Auth flow: Register → Login → Access protected routes
     - CRUD flow: Create → Read → Update → Delete
     - Data flow: Form input → API call → DB write → Response → UI update
     - Error flow: Invalid input → Validation error → Error message display

  2. For each flow, trace the code path:

LLM Prompt:
  "Trace this end-to-end user flow through the codebase.

   FLOW: User Registration → Login → Create First Task
   Step 1: User fills registration form
   Step 2: Frontend sends POST /register
   Step 3: Backend validates, creates user, returns token
   Step 4: Frontend stores token, redirects to login/dashboard
   Step 5: User logs in
   Step 6: Frontend sends POST /login, receives JWT
   Step 7: User creates a task
   Step 8: Frontend sends POST /tasks with auth header
   Step 9: Backend validates JWT, creates task, returns task
   Step 10: Frontend displays new task in list

   CODE:
   {relevant code files for this flow}

   For each step, determine:
   - Is this step implemented?
   - Does the output of step N correctly feed into step N+1?
   - Where does the flow break?

   Return ONLY valid JSON:
   {
     "flow_name": "Registration to First Task",
     "steps": [
       {
         "step": 1,
         "description": "User fills registration form",
         "implemented": true,
         "code_reference": "src/components/Register.tsx:15-30",
         "connects_to_next": true,
         "issues": []
       },
       {
         "step": 4,
         "description": "Frontend stores token, redirects",
         "implemented": false,
         "code_reference": null,
         "connects_to_next": false,
         "issues": ["Token is received but never stored — localStorage.setItem is missing", "No redirect after registration"]
       }
     ],
     "flow_complete": false,
     "breaks_at_step": 4,
     "flow_score": 6.0
   }"
```

#### Pass 5 — Test Scenario Generation

```
Purpose: Generate test scenarios that WOULD validate each requirement
         This serves as both a testing guide and a validation proof

LLM Prompt:
  "Based on the requirements and their implementation status, generate test scenarios.

   REQUIREMENTS AND STATUS:
   {validation_results summary}

   For each requirement, generate:
   1. Happy path test scenario
   2. Edge case test scenarios
   3. Negative test scenarios (what should fail)
   4. Whether the current code would pass each test

   Return ONLY valid JSON:
   {
     "test_scenarios": [
       {
         "requirement_id": "R001",
         "scenarios": [
           {
             "name": "Successful user registration",
             "type": "happy_path",
             "steps": [
               "Navigate to /register",
               "Enter valid email: test@example.com",
               "Enter valid password: SecurePass123!",
               "Click Submit",
               "Expect success message and redirect to login"
             ],
             "would_pass": true,
             "reason": "All steps have corresponding code"
           },
           {
             "name": "Duplicate email registration",
             "type": "edge_case",
             "steps": [
               "Register with email already in database",
               "Expect error message: 'Email already exists'"
             ],
             "would_pass": false,
             "reason": "Backend has no unique constraint on email field"
           },
           {
             "name": "SQL injection in email field",
             "type": "negative",
             "steps": [
               "Enter email: admin'--@evil.com",
               "Expect rejection, not SQL execution"
             ],
             "would_pass": true,
             "reason": "Pydantic EmailStr validator prevents injection"
           }
         ]
       }
     ],
     "total_scenarios": 24,
     "would_pass": 18,
     "would_fail": 6,
     "test_pass_rate": 75
   }"
```

#### Complete Output Structure

```json
{
  "functional_validation": {
    "parsed_requirements": [
      {
        "id": "R001",
        "category": "authentication",
        "title": "User Registration",
        "priority": "must_have",
        "acceptance_criteria": [...],
        "expected_evidence": {...}
      }
    ],

    "implicit_requirements": [...],

    "validation_results": [
      {
        "requirement_id": "R001",
        "overall_status": "partial",
        "evidence_coverage": 0.85,
        "functional_score": 7.5,
        "criteria_results": [
          {
            "criterion": "Registration form",
            "status": "met",
            "correctness": "correct",
            "evidence_file": "src/components/Register.tsx",
            "evidence_line": 15
          },
          {
            "criterion": "Duplicate email prevention",
            "status": "missing",
            "correctness": "not_implemented",
            "issues": ["No unique constraint on email in DB model"]
          }
        ],
        "edge_cases_handled": [...],
        "edge_cases_missing": [...],
        "bugs_found": [...]
      }
    ],

    "flow_validations": [
      {
        "flow_name": "Registration to First Task",
        "flow_complete": false,
        "breaks_at_step": 4,
        "steps": [...],
        "flow_score": 6.0
      }
    ],

    "test_scenarios": [...],

    "traceability_matrix": {
      "R001": {
        "frontend_files": ["Register.tsx"],
        "backend_files": ["auth.py", "user.py"],
        "test_files": [],
        "status": "partial",
        "score": 7.5
      }
    },

    "summary": {
      "total_requirements": 12,
      "must_have": { "total": 8, "met": 5, "partial": 2, "missing": 1 },
      "should_have": { "total": 3, "met": 2, "partial": 1, "missing": 0 },
      "nice_to_have": { "total": 1, "met": 0, "partial": 0, "missing": 1 },
      "completeness_score": 72,
      "correctness_score": 68,
      "functional_score": 7.0,
      "test_pass_rate": 75,
      "critical_bugs": 2,
      "flows_complete": 2,
      "flows_broken": 1
    },

    "gap_analysis": {
      "missing_features": [...],
      "partially_implemented": [...],
      "incorrectly_implemented": [...],
      "extra_features_not_required": [...],
      "priority_fixes": [
        {
          "requirement": "R001",
          "issue": "No duplicate email check",
          "impact": "critical — allows duplicate accounts",
          "fix_effort": "30 minutes",
          "fix_suggestion": "Add unique constraint to User.email in SQLAlchemy model"
        }
      ]
    }
  }
}
```

#### Scoring Formula

```
functional_score = (
  (must_have_met / must_have_total) × 0.50 +
  (should_have_met / should_have_total) × 0.25 +
  (correctness_score / 100) × 0.15 +
  (test_pass_rate / 100) × 0.10
) × 10

Penalty deductions:
  - Each critical bug: -0.5
  - Each broken flow: -0.3
  - Each missing must_have: -0.8
```

### Agent 14 — Plagiarism / Originality Detector

```
Input:  All files, structure_analysis
Output: originality_report with originality_estimate, boilerplate_percentage, tutorial_signals

Logic:
  1. Fingerprint boilerplate:
     - CRA default files (App.tsx, index.tsx, reportWebVitals)
     - Vite default files
     - FastAPI tutorial patterns (items, Item, fake_items_db)
     - Default README content
  2. Calculate custom code % = (total - boilerplate) / total
  3. Detect tutorial signals:
     - Common tutorial variable names (todos, posts, fakePosts)
     - Placeholder URLs (jsonplaceholder, example.com)
     - Copy-paste artifacts (commented tutorial steps)

LLM Analysis:
  - Send key files
  - Prompt: "Student work vs copy-pasted tutorial? What signs do you see?"
  - Prompt: "What percentage appears original?"

Scoring: originality_estimate / 10 (capped 0-10)
```

### Agent 15 — Complexity Analyzer

```
Input:  All source files
Output: complexity_report with maintainability_index, function_breakdown, refactoring_suggestions

Metrics Computed:
  - Cyclomatic Complexity: count if/elif/else/for/while/and/or/ternary per function
  - Cognitive Complexity: weighted nesting + flow breaks
  - Function-level breakdown: rank all functions by complexity
  - File-level aggregation
  - Distribution: low (1-5), moderate (6-10), high (11-15), danger (15+)

For Python: use `ast` module for precise parsing
For TypeScript: regex-based approximation (count branch keywords)

LLM Enhancement:
  - Send top-5 most complex functions
  - Prompt: "How would you refactor to reduce complexity? Show pseudo-code."

Scoring: Maintainability index normalized to 0-10
```

### Agent 16 — Report Generator (Enhanced)

```
Input:  All 15 agent outputs + profile config + rubric config
Output: Full report with overall_score, grade, category_scores, executive_summary, priority_actions, learning_path, all sections

Logic:
  1. Collect all agent scores
  2. Apply weights (from rubric if provided, else profile defaults)
  3. Calculate weighted overall score
  4. Determine grade (A/B/C/D/F)
  5. Aggregate all findings by type (critical/suggestion/strength)
  6. Rank critical issues by impact
  7. Generate priority action items (top 5 with time estimates)
  8. Generate code heat map data (file → issue count)

LLM Generation (3 Ollama calls):
  1. Executive Summary: 3-4 paragraphs addressing student
  2. Priority Actions: top 5 with specific fix instructions + time
  3. Learning Path: 2-week plan based on weakness areas

If previous version exists (re-review):
  4. Version comparison: resolved, persistent, new issues

Output: Complete report JSON with all sections populated
```

---

## 16. Enhanced Report Structure

```json
{
  "meta": {
    "session_id": "uuid",
    "student_name": "Alice",
    "project_id": "todo-app",
    "version": 3,
    "profile": "bootcamp",
    "rubric": null,
    "generated_at": "2026-03-19T10:30:00Z",
    "review_duration_seconds": 245
  },

  "scores": {
    "overall": 6.8,
    "grade": "B",
    "categories": {
      "code_quality": { "score": 7.2, "weight": 0.15, "weighted": 1.08 },
      "security": { "score": 5.8, "weight": 0.15, "weighted": 0.87 },
      "architecture": { "score": 7.5, "weight": 0.10, "weighted": 0.75 },
      "frontend": { "score": 8.1, "weight": 0.10, "weighted": 0.81 },
      "backend": { "score": 6.0, "weight": 0.10, "weighted": 0.60 },
      "testing": { "score": 3.5, "weight": 0.10, "weighted": 0.35 },
      "performance": { "score": 6.8, "weight": 0.10, "weighted": 0.68 },
      "documentation": { "score": 4.8, "weight": 0.05, "weighted": 0.24 },
      "accessibility": { "score": 5.5, "weight": 0.05, "weighted": 0.275 },
      "originality": { "score": 7.0, "weight": 0.05, "weighted": 0.35 },
      "requirements": { "score": 7.8, "weight": 0.05, "weighted": 0.39 }
    }
  },

  "executive_summary": "markdown string...",

  "priority_actions": [
    {
      "rank": 1,
      "severity": "critical",
      "title": "Add Error Boundaries",
      "detail": "...",
      "file": "src/App.tsx",
      "estimated_hours": 2,
      "category": "error_handling"
    }
  ],

  "findings": {
    "critical": [ { "type": "negative", "area": "...", "detail": "...", "file": "...", "line": 14, "fix_hint": "..." } ],
    "suggestions": [ ... ],
    "strengths": [ ... ]
  },

  "agents": {
    "structure": { ... },
    "react": { "score": 8.1, "sub_scores": {...}, "findings": [...], "llm_analysis": {...}, "stats": {...} },
    "fastapi": { ... },
    "security": { "severity_counts": {...}, "findings": [...], "owasp_coverage": {...} },
    "performance": { "frontend_perf": {...}, "backend_perf": {...} },
    "codesmell": { "smells": [...], "smell_density": 3.2 },
    "testcoverage": { "test_file_ratio": 0.3, "untested_critical_paths": [...], "test_quality": {...} },
    "dependencies": { "frontend_deps": {...}, "backend_deps": {...}, "concerns": [...] },
    "accessibility": { "violations": [...], "wcag_summary": {...} },
    "documentation": { "readme_score": 6.0, "docstring_coverage": {...} },
    "integration": { "backend_endpoints": [...], "frontend_api_calls": [...], "endpoint_map": {...} },
    "requirements": {
      "parsed_requirements": [
        {
          "id": "R001",
          "category": "authentication",
          "title": "User Registration",
          "priority": "must_have",
          "acceptance_criteria": [
            "Registration form with email and password",
            "Email format validation",
            "Password minimum length",
            "Duplicate email prevention",
            "Success confirmation"
          ],
          "expected_evidence": {
            "frontend": ["registration form component", "email input", "password input"],
            "backend": ["POST /register endpoint", "password hashing", "user creation"],
            "database": ["users table with email and password"]
          }
        }
      ],
      "implicit_requirements": [
        { "id": "IR001", "title": "Error Handling", "description": "Proper error responses for all ops" }
      ],
      "validation_results": [
        {
          "requirement_id": "R001",
          "overall_status": "partial",
          "evidence_coverage": 0.85,
          "functional_score": 7.5,
          "criteria_results": [
            {
              "criterion": "Registration form with email and password",
              "status": "met",
              "correctness": "correct",
              "evidence_file": "src/components/Register.tsx",
              "evidence_line": 15,
              "assessment": "Form exists with both fields",
              "issues": [],
              "severity": null
            },
            {
              "criterion": "Duplicate email prevention",
              "status": "missing",
              "correctness": "not_implemented",
              "evidence_file": null,
              "evidence_line": null,
              "assessment": "No unique constraint on email in DB model",
              "issues": ["Allows duplicate accounts"],
              "severity": "critical"
            }
          ],
          "edge_cases_handled": ["empty field validation"],
          "edge_cases_missing": ["duplicate email check", "password strength"],
          "bugs_found": [
            {
              "description": "No unique constraint on email field",
              "file": "backend/models/user.py",
              "line": 8,
              "severity": "critical",
              "fix": "Add unique=True to User.email column"
            }
          ]
        }
      ],
      "flow_validations": [
        {
          "flow_name": "Registration to First Task",
          "flow_complete": false,
          "breaks_at_step": 4,
          "steps": [
            { "step": 1, "description": "Fill registration form", "implemented": true, "connects_to_next": true },
            { "step": 2, "description": "POST /register", "implemented": true, "connects_to_next": true },
            { "step": 3, "description": "Backend creates user", "implemented": true, "connects_to_next": true },
            { "step": 4, "description": "Store token + redirect", "implemented": false, "issues": ["Token never stored", "No redirect"] }
          ],
          "flow_score": 6.0
        }
      ],
      "test_scenarios": {
        "total_scenarios": 24,
        "would_pass": 18,
        "would_fail": 6,
        "test_pass_rate": 75,
        "scenarios_by_requirement": [
          {
            "requirement_id": "R001",
            "scenarios": [
              { "name": "Successful registration", "type": "happy_path", "would_pass": true },
              { "name": "Duplicate email", "type": "edge_case", "would_pass": false, "reason": "No unique constraint" },
              { "name": "SQL injection in email", "type": "negative", "would_pass": true, "reason": "Pydantic validates" }
            ]
          }
        ]
      },
      "traceability_matrix": {
        "R001": { "frontend_files": ["Register.tsx"], "backend_files": ["auth.py", "user.py"], "test_files": [], "status": "partial" },
        "R002": { "frontend_files": ["Login.tsx"], "backend_files": ["auth.py"], "test_files": ["test_auth.py"], "status": "met" }
      },
      "summary": {
        "total_requirements": 12,
        "must_have": { "total": 8, "met": 5, "partial": 2, "missing": 1 },
        "should_have": { "total": 3, "met": 2, "partial": 1, "missing": 0 },
        "nice_to_have": { "total": 1, "met": 0, "partial": 0, "missing": 1 },
        "completeness_score": 72,
        "correctness_score": 68,
        "functional_score": 7.0,
        "test_pass_rate": 75,
        "critical_bugs": 2,
        "flows_complete": 2,
        "flows_broken": 1
      },
      "gap_analysis": {
        "missing_features": ["Role-Based Access Control"],
        "partially_implemented": ["Task CRUD — no Update or Delete"],
        "incorrectly_implemented": ["Token storage — received but never saved"],
        "extra_features": ["Dark mode toggle — not in requirements"],
        "priority_fixes": [
          {
            "requirement": "R001",
            "issue": "No duplicate email check",
            "impact": "critical — allows duplicate accounts",
            "fix_effort": "30 minutes",
            "fix_suggestion": "Add unique=True to User.email in SQLAlchemy model"
          }
        ]
      }
    },
    "plagiarism": { "originality_estimate": 65, "boilerplate_percentage": 25, "tutorial_signals": [...] },
    "complexity": { "maintainability_index": 62, "avg_cyclomatic": 4.2, "distribution": {...}, "danger_functions": [...] }
  },

  "architecture_diagrams": {
    "component_tree": "mermaid code...",
    "api_flow": "mermaid code...",
    "data_model": "mermaid code...",
    "full": "mermaid code..."
  },

  "learning_path": {
    "weeks": [
      {
        "week": 1,
        "items": [
          {
            "day": "1-2",
            "topic": "Error Handling in React",
            "why": "Your app crashes on any render error",
            "exercise": "Add ErrorBoundary wrapper + async error handling",
            "estimated_hours": 3
          }
        ]
      }
    ],
    "skill_gaps": { "error_handling": 3, "testing": 2, "security": 4, ... }
  },

  "code_heatmap": [
    { "file": "src/components/Dashboard.tsx", "issue_count": 8, "severity_sum": 14 },
    { "file": "backend/services/orders.py", "issue_count": 5, "severity_sum": 12 }
  ],

  "version_comparison": {
    "previous_version": 2,
    "resolved": [ ... ],
    "persistent": [ ... ],
    "new_issues": [ ... ],
    "score_delta": +1.1
  }
}
```

---

## 17. Tech Stack & Dependencies

### Backend

| Package | Purpose |
|---|---|
| `fastapi` | API framework |
| `uvicorn` | ASGI server |
| `httpx` | Async HTTP client for Ollama |
| `langgraph` | Agent orchestration with fan-out/fan-in |
| `python-multipart` | File upload handling |
| `aiosqlite` | Async SQLite for history |
| `radon` | Python cyclomatic complexity calculation |
| `mermaid-py` (optional) | Server-side Mermaid validation |

### Frontend

| Package | Purpose |
|---|---|
| `react` + `react-dom` | UI framework |
| `typescript` | Type safety |
| `vite` | Build tool |
| `tailwindcss` | Utility-first CSS |
| `zustand` | State management |
| `framer-motion` | Animations |
| `recharts` | Charts (radial gauges, line charts, bar charts, radar) |
| `react-dropzone` | File upload drag-and-drop |
| `react-markdown` | Render LLM markdown |
| `react-diff-viewer` | Side-by-side code diffs |
| `@monaco-editor/react` | Code viewer with syntax highlighting |
| `mermaid` | Architecture diagram rendering |
| `sonner` | Toast notifications |
| `html2canvas` + `jspdf` | PDF export |
| `lucide-react` | Icon set |

### Infrastructure

| Tool | Purpose |
|---|---|
| `Ollama` | Local LLM inference (qwen2.5:14b recommended) |
| `SQLite` | Review history, profiles, rubrics, chat |
| `Docker` + `docker-compose` | Containerized deployment |

---

## 18. Development Setup

### Backend

```bash
# Create project
mkdir codereview-agent && cd codereview-agent
mkdir backend && cd backend

# Virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install fastapi uvicorn httpx langgraph python-multipart aiosqlite radon

# Ensure Ollama is running
ollama pull qwen2.5:14b

# Run backend
python main.py  # → http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Frontend

```bash
cd ../frontend

# Scaffold
npm create vite@latest . -- --template react-ts

# Install dependencies
npm install zustand recharts framer-motion react-dropzone react-markdown
npm install react-diff-viewer-continued @monaco-editor/react mermaid sonner
npm install html2canvas jspdf lucide-react
npm install -D tailwindcss @tailwindcss/typography postcss autoprefixer

# Tailwind init
npx tailwindcss init -p

# Run frontend
npm run dev  # → http://localhost:5173
```

### Docker Compose (Full Stack)

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=qwen2.5:14b
    volumes:
      - ./data:/app/data    # SQLite persistence
    depends_on:
      - ollama

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

volumes:
  ollama_data:
```

---

## 19. Testing Plan

### Backend Testing

| Layer | Tool | What to Test |
|---|---|---|
| Agent Logic | pytest + pytest-asyncio | Each agent in isolation with fixture files |
| API Endpoints | pytest + httpx.AsyncClient | Upload, stream, chat, batch, history, profiles |
| SSE Streaming | pytest | Event format, ordering, error events |
| Database | pytest + aiosqlite | CRUD for reviews, profiles, rubrics, chat |
| Integration | pytest | Full pipeline with small test zips |
| Ollama Mocking | pytest-mock | Mock Ollama responses for deterministic tests |

Test fixtures: pre-built zip files with known code patterns for predictable agent outputs.

### Frontend Testing

| Layer | Tool | What to Test |
|---|---|---|
| Components | Vitest + React Testing Library | All component render states, user interactions |
| Store Logic | Vitest | State transitions, computed values, action effects |
| SSE Hook | Vitest (mock EventSource) | Event parsing, reconnect, timeout, cleanup |
| Upload Flow | Vitest + MSW | FormData, validation, error responses |
| Code Viewer | Vitest + RTL | Annotation rendering, navigation, Monaco load |
| Chat | Vitest + RTL | Message rendering, streaming append, suggested questions |
| Batch | Vitest + RTL | Multi-student list, comparison table sorting |
| History | Vitest + RTL | Progress chart data, version diff rendering |
| Profiles | Vitest + RTL | Profile editor, weight sliders, agent toggles |
| E2E | Playwright | Full flows: upload → progress → report → chat → export |
| Accessibility | axe-core + manual | Keyboard nav, screen reader, contrast ratios |
| Visual Regression | Playwright screenshots | Key screens at desktop/tablet/mobile breakpoints |

### Test Coverage Targets

| Area | Target |
|---|---|
| Backend agents | 85%+ |
| API endpoints | 90%+ |
| Frontend components | 80%+ |
| Store logic | 90%+ |
| E2E critical paths | 100% of main flows |

---

## 20. Implementation Phases

### Phase 1 — Foundation (Week 1-2)

**Backend:**
- [x] Agents 1-4 (Extract, Structure, React, FastAPI)
- [ ] Agent 12 (Integration Analyzer)
- [ ] Agent 13 (Requirements Validator)
- [ ] Agent 16 (Report Generator — basic version)
- [ ] Core API: POST /review, GET /review/{id}/stream, GET /health
- [ ] SQLite setup + reviews table

**Frontend:**
- [ ] Project scaffold (Vite + TS + Tailwind + Zustand)
- [ ] AppShell + Sidebar + Header
- [ ] Upload page (DropZone, FilePreview, ProblemStatement, SubmitButton)
- [ ] Progress page (AgentTimeline, LiveLog)
- [ ] Report page (OverallScoreCard, CategoryScoresGrid, ExecutiveSummary, FindingsPanel)
- [ ] SSE integration (useReviewStream hook)

### Phase 2 — Security & Quality Agents (Week 3-4)

**Backend:**
- [ ] Agent 5 (Security Scanner)
- [ ] Agent 7 (Code Smell Detector)
- [ ] Agent 15 (Complexity Analyzer)
- [ ] LangGraph fan-out/fan-in for parallel Phase 2 execution
- [ ] GET /review/{id}/file/{path} API

**Frontend:**
- [ ] SecurityReport section (SeverityBreakdown, OwaspCoverage)
- [ ] CodeSmellReport section (SmellDensityChart)
- [ ] ComplexityReport section (ComplexityDistribution, MostComplexFunctions)
- [ ] Code Viewer (CodeViewerPanel, Monaco Editor, GutterAnnotations)
- [ ] FindingCodeLink → opens code viewer

### Phase 3 — Deep Analysis Agents (Week 5-6)

**Backend:**
- [ ] Agent 6 (Performance Profiler)
- [ ] Agent 8 (Test Coverage Analyzer)
- [ ] Agent 9 (Dependency Auditor)
- [ ] Agent 10 (Accessibility Checker)
- [ ] Agent 11 (Documentation Scorer)
- [ ] All Phase 2 agents running in parallel

**Frontend:**
- [ ] PerformanceReport section
- [ ] TestCoverageReport section (CoverageGapMatrix, TestQualityMetrics)
- [ ] DependencyReport section
- [ ] AccessibilityReport section
- [ ] DocumentationReport section

### Phase 4 — AI Chat & Diff Views (Week 7-8)

**Backend:**
- [ ] POST /review/{id}/chat API (SSE streaming with report context)
- [ ] POST /review/{id}/fix-suggestion API
- [ ] Chat history in SQLite
- [ ] Agent 14 (Plagiarism Detector)

**Frontend:**
- [ ] ChatPanel (slide-out, message list, streaming, suggested questions)
- [ ] FindingDiffView (before/after with react-diff-viewer)
- [ ] OriginalityReport section

### Phase 5 — Batch Mode & History (Week 9-10)

**Backend:**
- [ ] POST /review/batch API
- [ ] GET /review/batch/{id}/stream API
- [ ] GET /review/batch/{id}/comparison API
- [ ] GET /history/{project_id} and /progress APIs
- [ ] Version comparison logic in Report Generator

**Frontend:**
- [ ] BatchUploadPage (multi-file drop, student names)
- [ ] BatchProgressPage (multi-student progress rows)
- [ ] ComparisonDashboard (table, class stats, common issues)
- [ ] HistoryPage (review list, search, filter)
- [ ] ProgressChart (score trend across versions)
- [ ] VersionComparison (resolved/persistent/new issues)

### Phase 6 — Profiles, Rubrics & Diagrams (Week 11-12)

**Backend:**
- [ ] Profile + Rubric CRUD APIs
- [ ] Profile-aware agent activation + weight application
- [ ] GET /review/{id}/diagram/{type} API
- [ ] Architecture diagram generation via Ollama

**Frontend:**
- [ ] ProfilesPage (list, editor, agent toggles, weight sliders)
- [ ] RubricEditor (category rows, weight validation)
- [ ] ProfileSelector + RubricSelector on upload page
- [ ] ArchitectureDiagram section (MermaidRenderer, DiagramTypeSelector)

### Phase 7 — Learning Path & Polish (Week 13-14)

**Backend:**
- [ ] Learning Path sub-agent in Report Generator
- [ ] Enhanced Report Generator (all sections populated)
- [ ] Performance optimization (caching, connection pooling)

**Frontend:**
- [ ] LearningPathPanel (WeekPlan, LearningItem, SkillGapRadar)
- [ ] PriorityActionItems component
- [ ] CodeHeatmap visualization
- [ ] Export: JSON, PDF, CSV, Copy Summary
- [ ] Light/Dark theme toggle
- [ ] Responsive layouts (tablet, mobile)
- [ ] Animation polish pass
- [ ] Accessibility audit of the dashboard itself

### Phase 8 — Testing & Hardening (Week 15-16)

- [ ] Backend: full pytest suite for all 16 agents
- [ ] Backend: API endpoint tests
- [ ] Frontend: Vitest + RTL for all components
- [ ] Frontend: Playwright E2E for all flows
- [ ] Frontend: Visual regression screenshots
- [ ] Frontend: axe-core accessibility audit
- [ ] Performance: optimize parallel agent execution
- [ ] Error handling: graceful degradation when agents fail
- [ ] Documentation: README, API docs, deployment guide

---

## 21. Known Gaps & Required Fixes

This section tracks identified gaps from design review. All items here must be resolved before the corresponding phase ships.

---

### HIGH IMPACT — Functional Blockers

#### H1 — Profile & Rubric Update/Delete APIs (Phase 6)

**Problem:** `PUT /profiles/{id}`, `DELETE /profiles/{id}`, `PUT /rubrics/{id}`, `DELETE /rubrics/{id}` were missing from the API surface. The `ProfileEditor` component has Save and Delete buttons that would have had no backend target.

**Fix applied:** Added all four endpoints to Section 3 API surface. `DELETE /profiles/{id}` must reject requests where `is_builtin = TRUE` (return 403).

**Frontend tasks:**
- [ ] `profileStore.updateProfile()` → `PUT /profiles/{id}`
- [ ] `profileStore.deleteProfile()` → `DELETE /profiles/{id}` (disable button for built-ins)
- [ ] `profileStore.updateRubric()` → `PUT /rubrics/{id}`
- [ ] `profileStore.deleteRubric()` → `DELETE /rubrics/{id}`

---

#### H2 — Cancel Review API + Store Action (Phase 1)

**Problem:** `CancelButton.tsx` in the progress page had no corresponding backend endpoint or store action.

**Fix applied:**
- Added `POST /review/{session_id}/cancel` to Section 3 API surface
- Added `cancelReview()` action to `reviewStore` actions list

**Frontend tasks:**
- [ ] Implement `cancelReview()` in `reviewStore.ts`: POST cancel → close SSE → `phase = "idle"`
- [ ] `CancelButton` calls `cancelReview()` with a `ConfirmDialog` before proceeding

**Backend tasks:**
- [ ] `POST /review/{session_id}/cancel` sets a cancellation flag checked by the LangGraph pipeline between agent transitions; in-progress agent is allowed to finish but no new agents are started

---

#### H3 — Fix Suggestion API Missing from API Surface (Phase 4)

**Problem:** `POST /review/{id}/fix-suggestion` is referenced in Feature F3 but was not listed in Section 3, making it invisible to backend devs.

**Fix applied:** Added `POST /review/{session_id}/fix-suggestion` to Section 3 with full request/response shape.

**Backend tasks:**
- [ ] Implement endpoint; cache results in SQLite keyed by `(session_id, finding_id)` to avoid redundant Ollama calls on repeated `[Show Fix]` clicks

---

#### H4 — History API Pagination & Delete (Phase 5)

**Problem:** `GET /history/{project_id}` returned an unbounded list. No delete endpoint existed.

**Fix applied:**
- Added `?page`, `?limit`, `?student_name`, `?sort` query params to `GET /history/{project_id}`
- Added `DELETE /history/{review_id}` endpoint

**Frontend tasks:**
- [ ] Update `historyStore.fetchHistory()` to pass pagination params and store `{ items, total, page }`
- [ ] Add pagination controls to `HistoryPage.tsx`
- [ ] Add delete button to `HistoryCard.tsx` (behind `ConfirmDialog`)
- [ ] `historyStore` — add `deleteReview(reviewId)` action

**Database tasks:**
- [ ] `DELETE /history/{review_id}` cascades to `chat_messages` for that session

---

### MEDIUM IMPACT — UX Gaps

#### M1 — Revalidation Trigger UI (Phase 3)

**Problem:** `POST /review/{session_id}/validation/revalidate` was defined in the API but no UI component existed to trigger it. The "student explains intent" workflow was described but not designed.

**Fix applied:** Added `RevalidatePanel.tsx` and `RevalidateStream.tsx` to the requirements component tree.

**Design spec for `RevalidatePanel`:**
- Appears below each `RequirementDetailModal` row with status `"partial"` or `"missing"`
- Contains a textarea: _"Explain your implementation intent for this requirement..."_
- "Re-validate" button triggers `POST /review/{id}/validation/revalidate` with `{ requirement_ids: [id], updated_problem_statement: text }`
- `RevalidateStream` connects to the returned SSE stream and updates only the affected requirement rows in place (no full-page reload)

---

#### M2 — Temp File Cleanup / Session Expiry (Phase 1 / Phase 8)

**Problem:** Extracted zip contents accumulated in the temp directory with no cleanup strategy.

**Fix applied:** Added ZIP validation + temp dir lifecycle to Agent 1 spec.

**Backend tasks:**
- [ ] On session creation, register `temp_dir = /tmp/sessions/{session_id}/` in the DB
- [ ] Background cleanup job (runs every hour): delete temp dirs for sessions older than 24h
- [ ] On `POST /review/{session_id}/cancel` or after report delivery, immediately schedule temp dir deletion (5-minute grace period for file serving via `GET /review/{id}/file/{path}`)

---

#### M3 — Agent Failure Isolation in LangGraph Fan-in (Phase 2)

**Problem:** Behavior was unspecified when a Phase 2 agent raised an exception. The fan-in could deadlock or abort the entire pipeline.

**Fix applied:** Added "Agent Failure Isolation" spec to Section 2 (Pipeline).

**Backend tasks:**
- [ ] Wrap each Phase 2 agent node in a `try/except`; on exception, return `AgentError` sentinel
- [ ] Fan-in node: collect all results including `AgentError` sentinels; do not block on errored nodes
- [ ] Report Generator: for each category whose agent errored, set `score = 0` and `note = "agent_failed"`
- [ ] SSE: emit `{ type: "error", agent: "<id>", message: "...", fatal: false }` so the frontend can mark the agent step as `"error"` without stopping the progress timeline

---

#### M4 — Batch SSE Reconnect Spec (Phase 5)

**Problem:** Single-review SSE had explicit reconnect/backoff logic but `useBatchStream` had no spec.

**Fix applied:** Added Batch SSE reconnect behaviour to Section 7 (SSE Integration).

**Backend tasks:**
- [ ] On reconnect to `GET /review/batch/{id}/stream`, replay `student_start` + `student_complete` (with score/grade) for all students that have already finished, then resume live events

**Frontend tasks:**
- [ ] `useBatchStream` — implement same 3-retry exponential backoff as `useReviewStream`
- [ ] On reconnect, received replay events must be idempotent (update existing student rows, not append duplicates)

---

#### M5 — `batchStore` Missing `problemStatement`, `profileId`, `rubricId`, `concurrencyLimit` (Phase 5)

**Problem:** The batch upload wireframe shows a problem statement field and profile/rubric selectors, but the `batchStore` state shape had none of these fields.

**Fix applied:** Added `problemStatement`, `profileId`, `rubricId`, and `concurrencyLimit` to `batchStore` state shape.

**Frontend tasks:**
- [ ] Add `setProblemStatement`, `setProfileId`, `setRubricId`, `setConcurrencyLimit` actions to `batchStore`
- [ ] Wire `BatchUploadPage` fields to these actions
- [ ] Pass `concurrency_limit` in `POST /review/batch` body (add to API surface)

---

#### M6 — `uiStore` Theme Persistence (Phase 7)

**Problem:** Theme preference was stored in Zustand memory only — reset to default on page refresh.

**Fix applied:** Added `zustand/middleware persist` spec to `uiStore`.

**Frontend tasks:**
- [ ] Wrap `uiStore` with `persist` middleware: `{ name: "ui-prefs", partialize: (s) => ({ theme: s.theme }) }`
- [ ] On app init, read persisted theme and apply `data-theme` attribute to `<html>` before first paint (prevents flash of wrong theme)
