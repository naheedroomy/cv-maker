---
phase: "1000-cover-letter-generator"
plan: "03"
subsystem: "api-integration"
tags: ["cover-letter", "fastapi", "vue3", "routing", "wiring"]
dependency_graph:
  requires:
    - "1000-01: generate_cover_letter(), render_cover_letter_pdf(), DB columns, API schemas"
    - "1000-02: CoverLetterSection.vue, ToneSelector.vue, Pinia store actions"
  provides:
    - "POST /api/jobs/:id/cover-letter — inline cover letter generation via asyncio.to_thread"
    - "PUT /api/jobs/:id/cover-letter — saves edited cover letter text to DB"
    - "GET /api/jobs/:id/cover-letter/pdf — returns PDF bytes with candidate name header"
    - "GET /api/jobs/:id returns cover_letter_text and cover_letter_notes fields"
    - "CoverLetterSection integrated into JobDetailView (visible when status=complete)"
  affects:
    - "frontend/src/views/JobDetailView.vue"
    - "backend/main.py"
    - "backend/routers/jobs.py"
tech_stack:
  added: []
  patterns:
    - "Inline asyncio.to_thread for cover letter generation (not background worker — fast ~5-15s)"
    - "Lazy provider imports inside endpoint to avoid circular imports at module load"
    - "BEGIN IMMEDIATE transaction pattern for DB writes (matches existing jobs router)"
    - "row.keys() guard on cover_letter columns for backward compatibility"
key_files:
  created:
    - "backend/routers/cover_letter.py"
  modified:
    - "backend/main.py"
    - "backend/routers/jobs.py"
    - "frontend/src/views/JobDetailView.vue"
decisions:
  - "CoverLetterSaveRequest defined locally in cover_letter.py rather than adding to schemas.py — it's an internal request type not shared across routers"
  - "Lazy imports of cv_maker modules inside endpoint functions — avoids potential circular import issues at module load time"
  - "CoverLetterSection uses v-if on status === complete in JobDetailView matching the component's internal guard — belt-and-suspenders"
metrics:
  duration: "~8min (Tasks 1-2 complete; Task 3 is human-verify checkpoint)"
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_created: 1
  files_modified: 3
---

# Phase 1000 Plan 03: Cover Letter API Wiring and Frontend Integration Summary

## One-liner

Cover letter API router (POST generate / PUT save / GET PDF) registered in FastAPI, _row_to_response updated to include cover letter fields, and CoverLetterSection wired into JobDetailView below gap analysis and tailoring notes.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Create cover letter API router and register in main.py, update jobs response helper | a851477 | backend/routers/cover_letter.py, backend/main.py, backend/routers/jobs.py |
| 2 | Integrate CoverLetterSection into JobDetailView | e0c5be9 | frontend/src/views/JobDetailView.vue |

## Task 3: Awaiting Human Verification

Task 3 is a `checkpoint:human-verify` gate. The full end-to-end cover letter flow requires browser verification before marking complete.

## What Was Built

### `backend/routers/cover_letter.py` (new)

- `POST /{job_id}/cover-letter`: Verifies job is complete + has tailored CV data, loads base CV, calls `generate_cover_letter()` via `asyncio.to_thread`, stores result in DB, returns `CoverLetterResponse`
- `PUT /{job_id}/cover-letter`: Saves edited cover letter text and notes to DB, returns updated `CoverLetterResponse`
- `GET /{job_id}/cover-letter/pdf`: Extracts candidate name from `tailored_cv_json`, calls `render_cover_letter_pdf()` via `asyncio.to_thread`, returns raw PDF bytes with `application/pdf` content type
- `CoverLetterSaveRequest` model defined locally (not in shared schemas — internal type only)
- All DB writes use `BEGIN IMMEDIATE` transaction pattern matching existing `jobs.py` conventions

### `backend/main.py` (modified)

- Imports `cover_letter_router` from `backend.routers.cover_letter`
- Registers with `api_router.include_router(cover_letter_router)` — appears after `jobs_router`, before `cv_convert_router`
- Routes now visible: `/api/jobs/{job_id}/cover-letter` (POST + PUT), `/api/jobs/{job_id}/cover-letter/pdf` (GET)

### `backend/routers/jobs.py` (modified)

- `_row_to_response` helper now includes:
  - `cover_letter_text=row["cover_letter_text"] if "cover_letter_text" in row.keys() else None`
  - `cover_letter_notes=row["cover_letter_notes"] if "cover_letter_notes" in row.keys() else None`
- `GET /api/jobs/:id` and `GET /api/jobs/` now return cover letter fields

### `frontend/src/views/JobDetailView.vue` (modified)

- Import: `import CoverLetterSection from '@/components/CoverLetterSection.vue'`
- `<CoverLetterSection>` element added after `<TailoringNotes>` and before the Job Listing Text section
- `v-if="currentJob.status === 'complete'"` guard ensures section only renders on complete jobs
- All 5 props bound: `job-id`, `job-status`, `current-model`, `existing-cover-letter`, `existing-notes`
- `vue-tsc --noEmit` passes cleanly

## Decisions Made

1. **CoverLetterSaveRequest defined locally**: The PUT endpoint needs its own request model. Adding it to `backend/schemas.py` would be correct but not necessary — it's not shared across routers. Keeping it local avoids cluttering the shared schema file.

2. **Lazy imports inside endpoint functions**: `cv_maker.cover_letter`, `cv_maker.cover_letter_renderer`, `cv_maker.models`, and `cv_maker.data` are imported inside the endpoint functions rather than at module top. This avoids potential circular import issues at module load time and is a common FastAPI pattern for heavy imports.

3. **Belt-and-suspenders v-if**: Both the parent (`v-if="currentJob.status === 'complete'"` in JobDetailView) and the child (`v-if="jobStatus === 'complete'"` in CoverLetterSection) guard the cover letter section. Redundant but safe.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all endpoints are fully implemented. The frontend integration passes all props from `currentJob` reactive state. No placeholder data flows to the UI.

## Self-Check: PASSED

- `backend/routers/cover_letter.py` exists: FOUND
- `backend/main.py` contains `cover_letter_router`: FOUND
- `backend/routers/jobs.py` contains `cover_letter_text` in `_row_to_response`: FOUND
- `frontend/src/views/JobDetailView.vue` imports CoverLetterSection: FOUND
- Commit a851477 (Task 1): FOUND
- Commit e0c5be9 (Task 2): FOUND
- Router import verified: `from backend.routers.cover_letter import router` — OK (3 routes)
- Routes verified: `/api/jobs/{job_id}/cover-letter` (POST + PUT), `/api/jobs/{job_id}/cover-letter/pdf` (GET) — all 3 registered in app
- TypeScript type check: `npx vue-tsc --noEmit` — PASSED (no errors)
