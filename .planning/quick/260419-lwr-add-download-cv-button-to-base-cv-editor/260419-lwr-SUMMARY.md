---
phase: quick-260419-lwr
plan: "01"
subsystem: cv-editor / pdf-pipeline
tags: [pdf, download, base-cv, latex, frontend, backend]
dependency_graph:
  requires: [core/renderer.py, backend/settings_cache.py, frontend/utils/apiFetch.ts]
  provides: [POST /api/cv/me/pdf, Download PDF button in BaseCvView]
  affects: [BaseCvView.vue, backend/routers/cv.py]
tech_stack:
  added: []
  patterns:
    - asyncio.to_thread wrapping blocking subprocess for render_pdf
    - BaseCV-to-TailoredCV conversion via model_dump() pass-through
    - Blob URL download pattern (createObjectURL + anchor click + revokeObjectURL)
key_files:
  created: []
  modified:
    - backend/routers/cv.py
    - frontend/src/views/BaseCvView.vue
decisions:
  - POST over GET for /cv/me/pdf: sends current in-memory CV body so unsaved edits are included, not just the DB-persisted version
  - asyncio.to_thread for render_pdf: latexmk subprocess is blocking; thread pool prevents blocking the ASGI event loop
  - btn-secondary for Download button: visually distinct from primary Save action, follows existing button class convention
metrics:
  duration: 79s
  completed: "2026-04-19"
  tasks: 2
  files_modified: 2
---

# Phase quick-260419-lwr Plan 01: Add Download CV Button to Base CV Editor Summary

**One-liner:** POST /cv/me/pdf endpoint renders in-memory BaseCV through LaTeX pipeline; Download PDF button in BaseCvView triggers browser file download with loading state.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add POST /cv/me/pdf backend endpoint | 29c02c6 | backend/routers/cv.py |
| 2 | Add Download PDF button to BaseCvView | ad1ea65 | frontend/src/views/BaseCvView.vue |

## What Was Built

### Backend: POST /cv/me/pdf

Added `download_base_cv_pdf` endpoint to `backend/routers/cv.py`:
- Accepts CV JSON body, validates with `BaseCV.model_validate()`
- Converts `BaseCV` to `TailoredCV` via `model_dump()` pass-through (extra fields default to `[]`)
- Renders LaTeX source via `render_latex(tailored)`
- Runs `render_pdf()` in thread pool via `asyncio.to_thread` (blocking subprocess)
- Looks up `cv_filename` setting per user; falls back to contact name if unset
- Returns `application/pdf` response with `Content-Disposition: attachment` header

### Frontend: Download PDF Button

Modified `frontend/src/views/BaseCvView.vue`:
- Added `apiFetch` import from `@/utils/apiFetch`
- Added `downloading` ref for button loading state
- Added `handleDownload()` async function: POST current `cv.value` JSON to `/api/cv/me/pdf`, create blob URL, trigger anchor click, revoke URL
- Error path sets `store.error` (shown in existing error banner)
- Button placed between "Save CV" (btn-primary) and "Remove CV" (btn-danger), uses `btn-secondary` class
- Shows "Rendering..." while LaTeX compilation runs on server

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

Files verified:
- `backend/routers/cv.py` — FOUND: `/cv/me/pdf` route in router.routes
- `frontend/src/views/BaseCvView.vue` — FOUND: handleDownload function and Download PDF button
- Commits verified: `29c02c6`, `ad1ea65` — present in git log
- TypeScript check: `vue-tsc --noEmit` exits 0 (no type errors)
