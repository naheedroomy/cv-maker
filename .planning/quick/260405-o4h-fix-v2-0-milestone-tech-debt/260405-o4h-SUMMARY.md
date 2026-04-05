---
phase: quick-260405-o4h
plan: 01
subsystem: backend, planning
tags: [tech-debt, sse, documentation, requirements, cleanup]
dependency_graph:
  requires: []
  provides:
    - "SSE complete event with full JobResponse-compatible payload (company_name, model, updated_at)"
    - "pipeline_runner.py with only live exports: run_provider_async and render_pdf_async"
    - "REQUIREMENTS.md with 35 complete requirements and no stale Pending statuses"
  affects:
    - "frontend/src/stores/jobStore.ts SSE complete handler (company_name and model now populated)"
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - backend/worker.py
    - backend/pipeline_runner.py
    - tests/test_pipeline_runner.py
    - .planning/REQUIREMENTS.md
decisions:
  - "_completed_at = _now_iso() shared between DB UPDATE and SSE push to avoid clock drift between write and push"
  - "created_at set to None in SSE complete event (not in local scope; frontend self-corrects via 30s sidebar poll)"
  - "run_pipeline_async tests removed alongside the dead export — they tested deleted code with no path to reuse"
metrics:
  duration: ~180s
  completed: "2026-04-05"
  tasks: 2
  files_modified: 4
---

# Quick Task 260405-o4h: Fix v2.0 Milestone Tech Debt Summary

**One-liner:** SSE complete event enriched with company_name/model/updated_at, dead run_pipeline_async removed, and REQUIREMENTS.md fully accurate with 35 complete requirements and 9 new Gemini entries.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix SSE complete event payload and remove dead export | f90be19 | backend/worker.py, backend/pipeline_runner.py, tests/test_pipeline_runner.py |
| 2 | Update REQUIREMENTS.md — fix statuses, add GEMINI reqs, fix FE-08 | 0d20b72 | .planning/REQUIREMENTS.md |

## What Was Done

### Task 1: Backend runtime fix + dead code removal

**worker.py** — The `full_result` dict pushed via `_push_event("complete", ...)` was missing `company_name`, `model`, `created_at`, and `updated_at`. These are present in `JobResponse` (the schema the frontend expects) but weren't being included, causing transient `undefined` fields in the UI until the 30-second sidebar poll refreshed.

Fixed by:
- Adding `_completed_at = _now_iso()` before the DB write
- Passing `_completed_at` to the DB UPDATE (eliminates tiny clock drift between write and push)
- Expanding `full_result` with `company_name`, `model`, `updated_at: _completed_at`, and `created_at: None` (not in local scope; frontend self-corrects)

**pipeline_runner.py** — `run_pipeline_async` was a dead export: it wrapped the old `run_pipeline()` from `cv_maker.pipeline`, which is superseded by the provider abstraction (`run_provider_async`). No callers remained in the backend. Removed the function and its now-unused `from cv_maker.pipeline import run_pipeline` import. Updated docstring to reflect the current two-function module.

**tests/test_pipeline_runner.py** — Three tests exclusively tested `run_pipeline_async` which was just removed. They imported the deleted name directly (no mock path workaround). Removed the three dead tests; kept the two `render_pdf_async` tests which remain valid.

### Task 2: REQUIREMENTS.md accuracy pass

- Marked 9 stale `[ ]` requirements as `[x]`: API-03, FE-01, FE-04, FE-05, FE-06, FE-07, FE-09, INT-01, INT-02
- Fixed FE-08 text from "Tailwind CSS for styling" to "Scoped CSS per component for styling (Tailwind was considered but scoped CSS chosen for component isolation)"
- Added new `### Gemini Provider (Phase 9)` section with GEMINI-01 through GEMINI-09 (all `[x]`)
- Updated traceability table: all 9 stale Pending rows flipped to Complete
- Added 9 GEMINI rows to traceability table
- Updated coverage footer: 26 → 35 total requirements
- Updated last-updated datestamp to 2026-04-05

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed dead tests for run_pipeline_async**
- **Found during:** Task 1 verification run
- **Issue:** `tests/test_pipeline_runner.py` had three tests (`test_run_pipeline_async_is_coroutine`, `test_run_pipeline_async_delegates_to_thread`, `test_run_pipeline_async_propagates_exception`) that imported `run_pipeline_async` directly. Removing the function caused ImportError and 3 test failures.
- **Fix:** Removed the three dead tests; added a note at the top of the file explaining why they were removed.
- **Files modified:** `tests/test_pipeline_runner.py`
- **Commit:** f90be19 (included in Task 1 commit)

## Known Stubs

None — all changes are either runtime fixes or documentation accuracy updates. No placeholder data flows to UI rendering.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| backend/worker.py exists | FOUND |
| backend/pipeline_runner.py exists | FOUND |
| tests/test_pipeline_runner.py exists | FOUND |
| .planning/REQUIREMENTS.md exists | FOUND |
| Commit f90be19 exists | FOUND |
| Commit 0d20b72 exists | FOUND |
