---
phase: 05-backend-foundation
plan: 01
subsystem: backend
tags: [sqlite, aiosqlite, fastapi, asyncio, tdd, database, async-wrappers]
dependency_graph:
  requires: []
  provides: [backend.db.init_db, backend.db.get_db, backend.db.DB_PATH, backend.pipeline_runner.run_pipeline_async, backend.pipeline_runner.render_pdf_async]
  affects: [05-02-PLAN.md]
tech_stack:
  added: [fastapi, uvicorn[standard], aiosqlite]
  patterns: [asyncio.to_thread, SQLite WAL mode, TDD red-green]
key_files:
  created:
    - backend/__init__.py
    - backend/routers/__init__.py
    - backend/db.py
    - backend/pipeline_runner.py
    - tests/test_db.py
    - tests/test_pipeline_runner.py
  modified:
    - pyproject.toml
    - uv.lock
decisions:
  - "asyncio.to_thread used to wrap both run_pipeline and render_pdf — consistent with STATE.md decision and prevents event loop blocking"
  - "db_path parameter added to init_db and get_db for testability via tmp_path fixture (no test pollution)"
  - "Tests use asyncio.run() in sync test functions — avoids pytest-asyncio dependency, simpler setup"
metrics:
  duration: "174 seconds (~3 minutes)"
  completed_date: "2026-04-04T06:22:57Z"
  tasks_completed: 3
  files_changed: 8
---

# Phase 5 Plan 1: Backend Dependencies, Database Module, and Async Pipeline Wrappers Summary

**One-liner:** SQLite backend with WAL mode + busy_timeout=5000 and asyncio.to_thread wrappers for subprocess-based pipeline and renderer.

## What Was Built

Three deliverables in a TDD workflow:

1. **Backend package scaffold** — `backend/__init__.py` and `backend/routers/__init__.py` with fastapi, uvicorn[standard], and aiosqlite added to pyproject.toml.

2. **`backend/db.py`** — SQLite database module with:
   - `init_db(db_path=None)` — creates file, enables WAL mode, sets busy_timeout=5000, creates jobs table with 10 columns
   - `get_db(db_path=None)` — returns connection with row_factory=aiosqlite.Row and busy_timeout=5000
   - `DB_PATH = Path("backend/cv_maker.db")` as the default path
   - db_path override parameter for test isolation using pytest tmp_path

3. **`backend/pipeline_runner.py`** — async wrappers:
   - `run_pipeline_async(base_cv, job_text)` — wraps `cv_maker.pipeline.run_pipeline` via `asyncio.to_thread`
   - `render_pdf_async(latex_source)` — wraps `cv_maker.renderer.render_pdf` via `asyncio.to_thread`

## Tests

- `tests/test_db.py` — 6 tests covering file creation, WAL mode, schema columns, busy_timeout, row_factory, idempotency
- `tests/test_pipeline_runner.py` — 5 tests covering coroutine check, asyncio.to_thread delegation (with mock), exception propagation

All 11 tests pass: `uv run pytest tests/test_db.py tests/test_pipeline_runner.py -v`

## Commits

| Hash    | Type | Description |
|---------|------|-------------|
| b8d7748 | chore | Install backend dependencies and scaffold backend package |
| 3b4baf5 | test  | Add failing tests for backend/db.py (RED) |
| c4afff1 | feat  | Implement backend/db.py — SQLite module with WAL mode (GREEN) |
| 73353b8 | test  | Add failing tests for backend/pipeline_runner.py (RED) |
| aa7b6fd | feat  | Implement backend/pipeline_runner.py — async wrappers (GREEN) |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no hardcoded empty values, placeholders, or unconnected data sources. All implementations are complete and tested.

## Self-Check: PASSED

Files verified:
- backend/__init__.py: EXISTS
- backend/routers/__init__.py: EXISTS
- backend/db.py: EXISTS
- backend/pipeline_runner.py: EXISTS
- tests/test_db.py: EXISTS
- tests/test_pipeline_runner.py: EXISTS

Commits verified: b8d7748, 3b4baf5, c4afff1, 73353b8, aa7b6fd — all present in git log.
