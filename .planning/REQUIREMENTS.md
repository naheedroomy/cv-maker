# Requirements: CV Maker v2.0

**Defined:** 2026-04-04
**Core Value:** Given a job listing and a base CV, produce a tailored CV that honestly highlights the most relevant experience and skills — never fabricate, only emphasize and reframe.

## v2.0 Requirements

Requirements for the full-stack rebuild. Each maps to roadmap phases.

### Backend & API

- [x] **API-01**: FastAPI backend serves all endpoints under /api/ prefix
- [x] **API-02**: Pipeline subprocess calls use asyncio.to_thread for non-blocking execution
- [x] **API-03**: Job queue uses asyncio.create_task with in-memory registry backed by SQLite
- [x] **API-04**: POST /api/jobs accepts company name, job link, job text and returns job ID
- [x] **API-05**: GET /api/jobs/:id returns job status (pending/running/complete/failed) and results
- [x] **API-06**: GET /api/jobs returns list of all jobs with status
- [x] **API-07**: DELETE /api/jobs/:id cancels an in-progress job
- [x] **API-08**: SSE endpoint streams real-time job status updates to connected clients
- [x] **API-09**: Structured logging with Python logging module visible in terminal
- [x] **API-10**: CORS configured for Vue dev server during development

### Database

- [x] **DB-01**: SQLite database with WAL mode and busy_timeout for concurrent access
- [x] **DB-02**: Jobs table stores company name, job link, job text, status, timestamps
- [x] **DB-03**: CV results stored as JSON (tailored_cv, gap_diff) with PDF file path reference
- [x] **DB-04**: Database initialized on app startup via FastAPI lifespan

### Frontend

- [x] **FE-01**: Vue 3 SPA with Vite build tooling
- [x] **FE-02**: Job submission form with company name, job link, and job text fields
- [x] **FE-03**: Session list sidebar showing all jobs as clickable threads (like chat)
- [x] **FE-04**: Job status display with real-time updates via SSE
- [x] **FE-05**: CV preview showing tailored sections when job completes
- [x] **FE-06**: Gap diff display with color-coded present/missing indicators
- [x] **FE-07**: PDF auto-saved to output/{company}/{CV-Name}.pdf on completion
- [x] **FE-08**: Scoped CSS per component for styling (Tailwind was considered but scoped CSS chosen for component isolation)
- [x] **FE-09**: Pinia store managing job state and SSE connection lifecycle

### Integration

- [x] **INT-01**: FastAPI serves Vue dist/ build via StaticFiles with html=True for SPA routing
- [x] **INT-02**: Vite dev server proxies /api/ requests to FastAPI backend
- [x] **INT-03**: Existing cv_maker/ package (models, pipeline, renderer, data) used unchanged

### Gemini Provider (Phase 9)

- [x] **GEMINI-01**: BaseProvider abstract class defining `.run(base_cv, job_text)` interface
- [x] **GEMINI-02**: ClaudeProvider wraps existing claude CLI pipeline via BaseProvider
- [x] **GEMINI-03**: GeminiProvider wraps google-genai SDK via BaseProvider
- [x] **GEMINI-04**: get_provider() factory returns correct provider from model string
- [x] **GEMINI-05**: GeminiProvider reads GEMINI_API_KEY lazily at call time (not startup)
- [x] **GEMINI-06**: Shared _build_prompt() used by both providers for identical CV tailoring prompt
- [x] **GEMINI-07**: GET /api/config returns gemini_available flag based on env var presence
- [x] **GEMINI-08**: ModelSelector Vue component with v-model binding for provider selection
- [x] **GEMINI-09**: Model field persisted in jobs table and threaded through worker → provider routing

## Future Requirements

Deferred beyond v2.0.

- **FUT-01**: Multiple LaTeX CV templates
- **FUT-02**: Tailoring rationale/change log
- **FUT-03**: ATS-friendliness scoring
- **FUT-04**: Streaming Claude output to frontend in real-time

## Out of Scope

| Feature | Reason |
|---------|--------|
| User accounts / authentication | Personal tool, single user |
| Job application tracking / ATS | CV generator, not a tracker |
| Docker containerization | Personal local tool |
| Production deployment (cloud hosting) | Runs locally |
| WebSocket for status updates | SSE is sufficient for unidirectional server→client |
| Celery/Redis job queue | Overkill for single-user tool |
| Axios HTTP client | Active supply chain compromise (use native fetch) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| API-01 | Phase 5 | Complete |
| API-02 | Phase 5 | Complete |
| API-09 | Phase 5 | Complete |
| API-10 | Phase 5 | Complete |
| DB-01 | Phase 5 | Complete |
| DB-02 | Phase 5 | Complete |
| DB-03 | Phase 5 | Complete |
| DB-04 | Phase 5 | Complete |
| API-03 | Phase 6 | Complete |
| API-04 | Phase 6 | Complete |
| API-05 | Phase 6 | Complete |
| API-06 | Phase 6 | Complete |
| API-07 | Phase 6 | Complete |
| API-08 | Phase 6 | Complete |
| FE-01 | Phase 7 | Complete |
| FE-02 | Phase 7 | Complete |
| FE-03 | Phase 7 | Complete |
| FE-04 | Phase 7 | Complete |
| FE-05 | Phase 7 | Complete |
| FE-06 | Phase 7 | Complete |
| FE-07 | Phase 7 | Complete |
| FE-08 | Phase 7 | Complete |
| FE-09 | Phase 7 | Complete |
| INT-01 | Phase 8 | Complete |
| INT-02 | Phase 8 | Complete |
| INT-03 | Phase 8 | Complete |
| GEMINI-01 | Phase 9 | Complete |
| GEMINI-02 | Phase 9 | Complete |
| GEMINI-03 | Phase 9 | Complete |
| GEMINI-04 | Phase 9 | Complete |
| GEMINI-05 | Phase 9 | Complete |
| GEMINI-06 | Phase 9 | Complete |
| GEMINI-07 | Phase 9 | Complete |
| GEMINI-08 | Phase 9 | Complete |
| GEMINI-09 | Phase 9 | Complete |

**Coverage:**
- v2.0 requirements: 35 total (26 original + 9 Gemini provider)
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-05 after v2.0 milestone audit — added GEMINI-01 through GEMINI-09, fixed stale Pending statuses, updated FE-08 to scoped CSS*
