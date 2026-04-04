# Roadmap: CV Maker

## Milestones

- **v1.0 MVP** - Phases 1-4 (shipped 2026-04-04)
- **v2.0 Full-Stack Rebuild** - Phases 5-8 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-4) - SHIPPED 2026-04-04</summary>

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Foundation** - Define the YAML base CV schema and Pydantic models that all downstream components share (completed 2026-04-03)
- [x] **Phase 2: LaTeX Renderer** - Build the Jinja2 + LaTeX + subprocess render pipeline in isolation before adding AI variability
- [x] **Phase 3: AI Pipeline** - Integrate Claude Code CLI for job analysis, CV tailoring, no-fabrication enforcement, and gap diff
- [x] **Phase 4: Streamlit UI** - Wire all components into a working Streamlit app with session state, history, and PDF download (completed 2026-04-04)

### Phase 1: Data Foundation
**Goal**: The base CV schema and shared data models are defined, validated, and ready to be consumed by all downstream components
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02
**Success Criteria** (what must be TRUE):
  1. A YAML file containing the user's full base CV loads without errors and validates against the Pydantic BaseCV model
  2. Invalid base CV fields (missing required keys, wrong types) are caught at load time with a clear error message
  3. The job listing can be represented as a plain string that flows through the pipeline without transformation
  4. All shared Pydantic models (BaseCV, JobRequirements, TailoredCV) are importable and instantiable with test data
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Scaffold uv project, define all Pydantic models, write YAML loader, sample base_cv.yaml, and pytest tests

### Phase 2: LaTeX Renderer
**Goal**: Given a TailoredCV data object, the renderer produces a valid PDF — independent of any AI component
**Depends on**: Phase 1
**Requirements**: OUT-01, OUT-02
**Success Criteria** (what must be TRUE):
  1. A hardcoded TailoredCV object renders to a PDF that opens and displays correctly formatted CV content
  2. LaTeX special characters in CV content (ampersands, percent signs, underscores) are escaped and do not break compilation
  3. The render function returns PDF bytes that can be written to disk or served via Streamlit download
  4. A LaTeX compilation error surfaces a readable error message rather than a silent failure
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Install MacTeX + Jinja2, build renderer.py (escape_latex, render_latex, render_pdf) and cv.tex.jinja template
- [x] 02-02-PLAN.md — Write test_renderer.py and human checkpoint to verify PDF visual output

### Phase 3: AI Pipeline
**Goal**: Given a base CV and a job listing, Claude Code CLI produces a tailored CV JSON object and a gap diff — with no fabricated content
**Depends on**: Phase 2
**Requirements**: AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07, DATA-03, LAY-01
**Success Criteria** (what must be TRUE):
  1. Pasting a real job listing produces a TailoredCV where every bullet point references only skills and experience present in the base CV
  2. The gap diff correctly identifies job requirements the base CV does not cover and flags them to the user
  3. Claude Code CLI is invoked with `claude -p` in non-interactive mode and returns parseable JSON; a malformed response triggers a retry and eventually a clear error
  4. Skills and technologies present in the base CV but not featured in the work experience are surfaced in the tailored output when relevant to the job
  5. CV sections are reordered in the output to lead with the most relevant content for the target job
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Extend models.py with GapItem and JobAnalysis Pydantic models
- [x] 03-02-PLAN.md — Implement pipeline.py with two-step Claude invocation, retry loop, and no-fabrication enforcement
- [x] 03-03-PLAN.md — Write test_pipeline.py with monkeypatched subprocess tests

### Phase 4: Streamlit UI
**Goal**: Users can run the full pipeline — paste a job listing, generate a tailored CV, preview it, download the PDF, and revisit past runs — entirely through a browser UI
**Depends on**: Phase 3
**Requirements**: UI-01, UI-02, OUT-03, OUT-04, HIST-01, HIST-02
**Success Criteria** (what must be TRUE):
  1. User pastes a job listing, clicks Generate, and receives a downloadable tailored PDF without leaving the browser
  2. Interacting with Streamlit widgets (scrolling, clicking non-Generate buttons) does not re-trigger Claude Code CLI calls
  3. User can preview the tailored CV content in the UI before downloading the PDF
  4. Past (job listing, tailored CV) pairs are stored locally and the user can browse and open any previous run
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Install streamlit + pandas, implement app.py with session_state guard, gap table, CV preview, PDF download
- [x] 04-02-PLAN.md — Add history save/load and sidebar browser to app.py; human smoke test checkpoint

</details>

---

### v2.0 Full-Stack Rebuild (In Progress)

**Milestone Goal:** Replace Streamlit with FastAPI backend + Vue.js SPA frontend, add SQLite persistence, and enable concurrent CV generation with real-time job status tracking.

- [ ] **Phase 5: Backend Foundation** - FastAPI scaffold, async pipeline refactor, SQLite schema, CORS, and structured logging
- [ ] **Phase 6: Job Queue & API** - In-process asyncio job queue, worker, and all API endpoints including SSE and job cancellation
- [ ] **Phase 7: Vue Frontend** - Vue 3 SPA with Pinia state management, job submission, real-time status, CV preview, and PDF download
- [ ] **Phase 8: Production Wiring** - Vite build served by FastAPI, Streamlit retirement, and end-to-end smoke test

## Phase Details

### Phase 5: Backend Foundation
**Goal**: FastAPI serves the application, the existing cv_maker pipeline runs without blocking the event loop, SQLite is initialized, CORS is configured, and structured logging is visible in terminal
**Depends on**: Phase 4
**Requirements**: API-01, API-02, API-09, API-10, DB-01, DB-02, DB-03, DB-04
**Success Criteria** (what must be TRUE):
  1. `uvicorn backend.main:app` starts without error and `curl localhost:8000/api/` returns a response
  2. The existing `run_pipeline()` and `render_pdf()` calls are wrapped in `asyncio.to_thread` — running them does not freeze other concurrent requests
  3. SQLite database initializes on startup with WAL mode enabled; `backend/db.py` `init_db()` creates the jobs schema
  4. A request from the Vue dev server origin (`localhost:5173`) is not rejected with a CORS error
  5. Backend log lines (request received, job status change, errors) appear in the terminal where uvicorn runs
**Plans**: 2 plans
**UI hint**: no

Plans:
- [x] 05-01-PLAN.md — Install dependencies, scaffold backend package, create db.py (SQLite + WAL) and pipeline_runner.py (asyncio.to_thread wrappers)
- [x] 05-02-PLAN.md — Create main.py (FastAPI app with lifespan, CORS, logging, health check, task registry) and integration tests

### Phase 6: Job Queue & API
**Goal**: Users can submit a CV generation job via HTTP, the job runs concurrently in the background, and all job lifecycle endpoints return correct status and results
**Depends on**: Phase 5
**Requirements**: API-03, API-04, API-05, API-06, API-07, API-08
**Success Criteria** (what must be TRUE):
  1. `POST /api/jobs` returns a job ID immediately (before pipeline completes) and the job runs in the background
  2. `GET /api/jobs/:id` returns the correct status (pending/running/complete/failed) at each stage of the pipeline
  3. `GET /api/jobs` returns a list of all submitted jobs with their current status
  4. `DELETE /api/jobs/:id` cancels an in-progress job and subsequent status calls reflect cancellation
  5. An SSE client connected to the SSE endpoint receives real-time status push events as the job progresses
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md — Pydantic request/response schemas and background job worker coroutine with semaphore and SSE queue system
- [x] 06-02-PLAN.md — Jobs router with all six endpoints (CRUD, SSE, PDF) wired into FastAPI app
- [x] 06-03-PLAN.md — Integration tests for worker and all router endpoints

### Phase 7: Vue Frontend
**Goal**: Users can submit a job, watch it progress in real time, browse past sessions, preview the tailored CV, and download the PDF — all without leaving the browser
**Depends on**: Phase 6
**Requirements**: FE-01, FE-02, FE-03, FE-04, FE-05, FE-06, FE-07, FE-08, FE-09
**Success Criteria** (what must be TRUE):
  1. User fills the job submission form (company name, job link, job text) and submits — the UI acknowledges immediately with a pending status
  2. Job status updates appear in the UI in real time without manual refresh (via SSE or polling)
  3. The sidebar shows all past sessions as clickable entries; clicking one navigates to that session's results
  4. On a completed job, the user can read the tailored CV sections and gap diff directly in the browser
  5. User can download the generated PDF from the job detail view; the PDF is also auto-saved to `output/{company}/`
**Plans**: 3 plans
**UI hint**: yes

Plans:
- [x] 07-01-PLAN.md — Scaffold Vue 3 project, Vite proxy, TypeScript types, Pinia store with SSE lifecycle, Vue Router, App.vue shell
- [x] 07-02-PLAN.md — Sidebar with session list and polling, StatusBadge, SessionEntry, ErrorBanner, LoadingSpinner, JobFormView with validation
- [ ] 07-03-PLAN.md — JobDetailView with SSE, CvPreview, GapDiffTable, SkeletonSection, PDF download, Cancel Job, and human-verify checkpoint

### Phase 8: Production Wiring
**Goal**: A single `uvicorn` command serves both the API and the Vue SPA; Streamlit and its dependencies are removed; direct URL navigation works correctly
**Depends on**: Phase 7
**Requirements**: INT-01, INT-02, INT-03
**Success Criteria** (what must be TRUE):
  1. Running `vite build` and then `uvicorn backend.main:app` serves the full application — no separate Vite dev server needed
  2. Navigating directly to a frontend route (e.g., `/jobs/abc-123`) loads the SPA correctly rather than returning a 404
  3. `app.py`, `streamlit`, and `pandas` are removed from the project; the existing `cv_maker/` package is unchanged
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 5 → 6 → 7 → 8

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 1/1 | Complete | 2026-04-03 |
| 2. LaTeX Renderer | v1.0 | 2/2 | Complete | 2026-04-04 |
| 3. AI Pipeline | v1.0 | 3/3 | Complete | 2026-04-04 |
| 4. Streamlit UI | v1.0 | 2/2 | Complete | 2026-04-04 |
| 5. Backend Foundation | v2.0 | 2/2 | Complete |  |
| 6. Job Queue & API | v2.0 | 2/3 | In Progress|  |
| 7. Vue Frontend | v2.0 | 2/3 | In Progress|  |
| 8. Production Wiring | v2.0 | 0/TBD | Not started | - |
