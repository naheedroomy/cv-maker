---
phase: 09-add-gemini-2-5-flash-as-alternative-ai-provider-with-model-selector-in-vue-ui
plan: "04"
subsystem: tests
tags: [gap-closure, test-maintenance, worker, db]
dependency_graph:
  requires: [09-01, 09-02]
  provides: [green-test-suite]
  affects: [tests/test_worker.py, tests/test_db.py]
tech_stack:
  added: []
  patterns: [mock-target-patching, pytest-asyncio-run]
key_files:
  modified:
    - tests/test_worker.py
    - tests/test_db.py
decisions:
  - "GapItem helper updated to use match_level='strong' instead of stale present=True field"
metrics:
  duration: 180s
  completed: "2026-04-05T11:40:45Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 09 Plan 04: Gap Closure (Stale Test Fix) Summary

**One-liner:** Fixed two stale test files (4 dead mock targets + 1 missing DB column) to restore 11/11 green tests after Phase 09 Plans 01-02 refactored worker and database.

## What Was Done

Two test files were not updated when Phase 09 Plans 01-02 refactored the backend:

1. **tests/test_worker.py** — 4 `patch()` calls used the dead symbol `backend.worker.run_pipeline_async` (removed in Plan 02). The patches were inert, causing real pipeline invocations and test failures. Updated all 4 to `backend.worker.run_provider_async`.

2. **tests/test_db.py** — `test_init_db_jobs_table_columns` expected 10 columns but the `jobs` table now has 11 (the `model` column was added via idempotent ALTER TABLE migration in Plan 02). Updated `expected_columns` set and docstring.

## Results

- `tests/test_worker.py` + `tests/test_db.py`: **11/11 tests PASSED**
- Zero occurrences of `run_pipeline_async` in `tests/test_worker.py`
- `run_provider_async` appears exactly 4 times in `tests/test_worker.py`
- `"model"` present in `expected_columns` set in `tests/test_db.py`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale `_fake_gap_items()` helper using removed field `present`**
- **Found during:** Task 1 — running the 4 worker behavior tests after fixing mock targets
- **Issue:** `_fake_gap_items()` constructed `GapItem(requirement="Python", present=True, evidence="5 years exp")`. The `present: bool` field was replaced by `match_level: str` in the `GapItem` model during Phase 09 Plan 01. Pydantic v2 raised a `ValidationError` for missing required field `match_level`.
- **Fix:** Updated `_fake_gap_items()` to use `GapItem(requirement="Python", match_level="strong", evidence="5 years exp")`
- **Files modified:** `tests/test_worker.py` (line 67)
- **Commit:** included in `5914cdb`

## Known Stubs

None — this plan only modifies test files. No production code stubs introduced.

## Self-Check: PASSED

- tests/test_worker.py modified: FOUND
- tests/test_db.py modified: FOUND
- Commit 5914cdb: FOUND
- Commit 91dbf1c: FOUND
