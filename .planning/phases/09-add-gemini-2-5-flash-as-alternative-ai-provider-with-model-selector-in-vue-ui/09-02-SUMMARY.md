---
phase: 09-add-gemini-2-5-flash-as-alternative-ai-provider-with-model-selector-in-vue-ui
plan: 02
subsystem: backend
tags: [sqlite-migration, pydantic, fastapi, provider-routing, model-selector, python]

# Dependency graph
requires:
  - phase: 09-01
    provides: get_provider() factory, BaseProvider ABC, ClaudeProvider, GeminiProvider
provides:
  - Idempotent SQLite migration adding model column to jobs table
  - model field in JobCreate (default: claude-haiku) and JobResponse schemas
  - GET /api/config endpoint reporting gemini_available based on GEMINI_API_KEY
  - Provider-routed job_worker() dispatching via get_provider(model)
  - run_provider_async() wrapper in pipeline_runner.py for any BaseProvider
  - model field persisted and returned through full jobs API (INSERT, list, detail)
affects:
  - 09-03 (Vue UI model selector — reads /api/config and sends model in POST /api/jobs)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Idempotent SQLite column migration using PRAGMA table_info before ALTER TABLE
    - Provider-agnostic async wrapper (run_provider_async) for strategy-pattern providers
    - Feature flag endpoint (GET /api/config) for frontend capability detection

key-files:
  created:
    - backend/routers/config.py
  modified:
    - backend/db.py
    - backend/schemas.py
    - backend/worker.py
    - backend/pipeline_runner.py
    - backend/routers/jobs.py
    - backend/main.py

key-decisions:
  - "Idempotent migration guards ALTER TABLE with PRAGMA table_info check — no error on repeated startups"
  - "run_provider_async() added alongside existing run_pipeline_async() for backward compatibility — run_pipeline_async() kept for tests"
  - "GET /api/config uses os.environ.get with bool() cast — simple, no Pydantic settings overhead needed"

patterns-established:
  - "PRAGMA table_info pattern: check existing columns before ALTER TABLE for zero-downtime schema migration"
  - "Feature flag endpoint: GET /api/config returns capability booleans for frontend model availability detection"

requirements-completed: [GEMINI-05, GEMINI-06, GEMINI-07]

# Metrics
duration: 3min
completed: 2026-04-05
---

# Phase 9 Plan 02: Backend Data Layer and API Model Field Summary

**SQLite idempotent migration, model field end-to-end through schemas and worker routing, and GET /api/config feature flag endpoint for Gemini availability detection**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-05T05:42:23Z
- **Completed:** 2026-04-05T05:45:32Z
- **Tasks:** 2
- **Files modified:** 7 (6 modified, 1 created)

## Accomplishments

- Added `model` column to `_SCHEMA` CREATE TABLE and guarded ALTER TABLE migration with `PRAGMA table_info` for idempotent startup
- Added `model: str = "claude-haiku"` to `JobCreate` and `JobResponse` Pydantic schemas
- Created `backend/routers/config.py` with `GET /api/config` returning `{"gemini_available": bool(GEMINI_API_KEY)}`
- Added `run_provider_async()` to `pipeline_runner.py` — provider-agnostic async wrapper calling any `BaseProvider.run()`
- Updated `job_worker()` signature to accept `model` parameter; routes via `get_provider(model)` to correct AI provider
- Updated `jobs.py` INSERT, `_row_to_response`, and `create_job` return to include `model` field throughout
- Registered `config_router` in `main.py`; all imports resolve; ruff passes on all modified files

## Task Commits

Each task was committed atomically:

1. **Task 1: DB migration, schema updates, and config endpoint** - `cb47850` (feat)
2. **Task 2: Wire worker routing, jobs router, and main.py registration** - `0818dad` (feat)

## Files Created/Modified

- `backend/db.py` - model column in _SCHEMA; idempotent PRAGMA table_info migration in init_db()
- `backend/schemas.py` - model: str = "claude-haiku" on JobCreate and JobResponse
- `backend/routers/config.py` - GET /api/config endpoint with gemini_available flag
- `backend/pipeline_runner.py` - run_provider_async() added; BaseProvider import added
- `backend/worker.py` - model param on job_worker(); get_provider(model) routing; run_provider_async() call
- `backend/routers/jobs.py` - model field in INSERT SQL, _row_to_response, create_job response, job_worker call
- `backend/main.py` - config_router import and api_router.include_router(config_router)

## Decisions Made

- Idempotent migration uses `PRAGMA table_info` column check before `ALTER TABLE` — no error on repeated server restarts against an already-migrated database
- `run_provider_async()` added alongside existing `run_pipeline_async()` (not replacing it) — preserves backward compatibility for existing tests
- `GET /api/config` uses `os.environ.get("GEMINI_API_KEY")` with `bool()` cast — a simple one-liner is sufficient; no Pydantic Settings needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff E501/I001 lint violations in modified files**
- **Found during:** Task 2 (ruff check on modified files)
- **Issue:** Several lines exceeded the 100-char line-length limit after adding model parameters; import block in jobs.py was unsorted after editing
- **Fix:** Wrapped long function signature and logger.info calls; split INSERT string literal; used `ruff --fix` for import sort
- **Files modified:** backend/worker.py, backend/routers/jobs.py
- **Commit:** 0818dad (included in Task 2 commit)

**2. [Out of scope] Pre-existing F541 error in cv_convert.py**
- **Found during:** Task 2 (ruff check backend/)
- **Issue:** `backend/routers/cv_convert.py:55` has `f"CV parsed and saved as base_cv.yaml"` (f-string without placeholders) — pre-existing, not introduced by this plan
- **Fix:** Logged to deferred items; NOT fixed (out of scope per deviation rules)

---

**Total deviations:** 1 auto-fixed (Rule 1 — lint); 1 deferred (pre-existing, out of scope)
**Impact on plan:** Lint fix corrected code style; no behavior change.

## Known Stubs

None — all fields are wired through to the database and API responses with real values.

## User Setup Required

- `GEMINI_API_KEY` environment variable must be set when using `gemini-flash` model
- Source: Google AI Studio (https://aistudio.google.com/apikey) -> Create API key
- Without it, `GET /api/config` returns `{"gemini_available": false}`; Gemini job submissions will fail at pipeline execution time

## Next Phase Readiness

- 09-03 (Vue UI model selector) can now:
  - Call `GET /api/config` to determine whether to show the Gemini option
  - Send `model: "gemini-flash"` in `POST /api/jobs` body
  - Display `model` field from `GET /api/jobs/:id` response

---
*Phase: 09-add-gemini-2-5-flash-as-alternative-ai-provider-with-model-selector-in-vue-ui*
*Completed: 2026-04-05*

## Self-Check: PASSED

- FOUND: backend/db.py
- FOUND: backend/schemas.py
- FOUND: backend/routers/config.py
- FOUND: backend/worker.py
- FOUND: backend/pipeline_runner.py
- FOUND: backend/routers/jobs.py
- FOUND: backend/main.py
- FOUND commit: cb47850 (Task 1)
- FOUND commit: 0818dad (Task 2)
