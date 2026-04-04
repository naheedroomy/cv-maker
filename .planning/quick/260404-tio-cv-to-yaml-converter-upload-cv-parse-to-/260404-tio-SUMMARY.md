---
phase: quick
plan: 260404-tio
subsystem: cv-converter
tags: [cv-converter, backend, frontend, claude-cli, yaml]
dependency_graph:
  requires: []
  provides:
    - POST /api/cv/convert endpoint
    - src/cv_maker/cv_converter.py (convert_cv_to_yaml, save_base_cv)
    - frontend /convert page
    - Sidebar Import CV navigation
  affects:
    - base_cv.yaml (overwritten on successful conversion)
    - backend/main.py (new router registered)
    - backend/schemas.py (new request/response models added)
tech_stack:
  added:
    - cv_maker.cv_converter module
    - backend.routers.cv_convert router
    - CvConverterView.vue page
  patterns:
    - asyncio.to_thread wraps subprocess.run (matches existing pipeline pattern)
    - _invoke_with_retry reuse from pipeline.py (no duplication)
    - structured error responses (success: bool) instead of HTTP error codes for parse failures
    - lazy route import for CvConverterView
key_files:
  created:
    - src/cv_maker/cv_converter.py
    - backend/routers/cv_convert.py
    - frontend/src/views/CvConverterView.vue
  modified:
    - backend/schemas.py
    - backend/main.py
    - frontend/src/router/index.ts
    - frontend/src/components/AppSidebar.vue
decisions:
  - "Reuse _invoke_with_retry from pipeline.py directly — no duplication of Claude invocation logic"
  - "Return structured CvConvertResponse(success=False) for parse failures instead of HTTP 4xx — frontend displays errors cleanly without needing error handling for status codes"
  - "Only .txt file upload supported in frontend; PDFs require copy-paste — avoids adding a PDF parsing library dependency for MVP"
  - "asyncio.to_thread wraps both convert_cv_to_yaml() and save_base_cv() — consistent with existing pipeline_runner.py pattern for subprocess and disk I/O"
metrics:
  duration_seconds: 139
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_created: 3
  files_modified: 4
---

# Phase quick Plan 260404-tio: CV-to-YAML Converter Summary

**One-liner:** CV text-to-YAML converter using Claude CLI subprocess with BaseCV Pydantic validation, exposed via POST /api/cv/convert and a textarea-based Vue page at /convert.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Backend — converter module and API endpoint | 235a0d6 | src/cv_maker/cv_converter.py, backend/routers/cv_convert.py, backend/schemas.py, backend/main.py |
| 2 | Frontend — CV converter page with upload form and sidebar nav | 54b4764 | frontend/src/views/CvConverterView.vue, frontend/src/router/index.ts, frontend/src/components/AppSidebar.vue |

## What Was Built

### Backend

**`src/cv_maker/cv_converter.py`** — Core conversion logic:
- `convert_cv_to_yaml(cv_text: str) -> BaseCV`: Builds a structured prompt instructing Claude to extract CV data into the exact BaseCV JSON schema. Delegates to `_invoke_with_retry` (reused from pipeline.py — no duplication). Handles date normalization instructions, no-fabrication constraint, and retry logic.
- `save_base_cv(cv: BaseCV, path: Path | None = None) -> Path`: Serializes BaseCV to YAML via `yaml.dump(cv.model_dump(), ...)` and writes to `DEFAULT_CV_PATH` (base_cv.yaml).

**`backend/routers/cv_convert.py`** — FastAPI router:
- `POST /cv/convert` accepting `CvConvertRequest` body.
- Wraps both `convert_cv_to_yaml()` and `save_base_cv()` in `asyncio.to_thread()` — matches the existing `pipeline_runner.py` pattern for blocking calls.
- Returns `CvConvertResponse(success=False, message=...)` for parse failures (not HTTPException) — frontend can display error text without handling HTTP status codes.
- Raises `HTTPException(500)` only for unexpected (non-parse) errors.

**`backend/schemas.py`** additions:
- `CvConvertRequest(cv_text: str)`
- `CvConvertResponse(success: bool, message: str, contact_name: str | None)`

**`backend/main.py`**: `cv_convert_router` registered at `/api/cv/convert`.

### Frontend

**`frontend/src/views/CvConverterView.vue`**:
- Textarea-based form (14 rows) for pasting CV text.
- File input accepting `.txt` files — reads via `FileReader.readAsText()` and populates the textarea. Shows an inline error if a non-.txt file (e.g. PDF) is selected.
- Convert button: disabled while processing, shows spinner and "Converting..." text.
- POSTs `{ cv_text }` to `/api/cv/convert` using native `fetch` (no axios — per project decision).
- Success banner (green) showing message and contact name.
- Error banner (red) for parse failures and network errors.
- Styled with scoped CSS matching JobFormView.vue conventions (system-ui font, #111827 text, #2563eb buttons, #e2e8f0 borders).

**`frontend/src/router/index.ts`**: `/convert` route added with lazy-loaded `CvConverterView`.

**`frontend/src/components/AppSidebar.vue`**: "Import CV" RouterLink added below the "New Job" button in the sidebar header.

## Decisions Made

1. **Reuse `_invoke_with_retry` from pipeline.py** — imports the private helper directly rather than duplicating it. This is correct since it is in the same package and cv_converter.py is also part of `cv_maker`.

2. **Structured error response instead of HTTP 4xx** — `CvConvertResponse(success=False)` allows the frontend to display clean error messages without needing `try/catch` on fetch status codes.

3. **No PDF binary parsing in MVP** — frontend accepts `.txt` uploads only; PDFs require copy-paste. Avoids adding `pdfminer`, `PyMuPDF`, or similar as a new dependency for a bootstrap-helper feature.

4. **`asyncio.to_thread` for both subprocess and disk I/O** — consistent with the established pattern in `pipeline_runner.py`.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — the converter wires directly to Claude CLI and writes to the real `base_cv.yaml`. No placeholder data flows to any UI rendering.

## Self-Check: PASSED

Files created/exist:
- src/cv_maker/cv_converter.py: FOUND
- backend/routers/cv_convert.py: FOUND
- frontend/src/views/CvConverterView.vue: FOUND

Commits verified:
- 235a0d6: FOUND (feat(260404-tio): add CV converter module and POST /api/cv/convert endpoint)
- 54b4764: FOUND (feat(260404-tio): add CV converter page, /convert route, and Import CV sidebar link)
