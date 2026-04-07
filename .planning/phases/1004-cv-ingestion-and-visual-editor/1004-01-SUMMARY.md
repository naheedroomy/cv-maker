---
phase: 1004-cv-ingestion-and-visual-editor
plan: "01"
subsystem: backend
tags: [cv-parsing, pdf, gemini, fastapi, crud, pymupdf]
dependency_graph:
  requires: []
  provides:
    - core/cv_parser.py::parse_pdf_to_base_cv
    - backend/routers/cv.py::router (POST /upload, GET /me, PUT /me, DELETE /me)
    - backend/schemas.py::CvUploadResponse
    - backend/schemas.py::CvMeResponse
  affects:
    - backend/main.py (router registration)
    - backend/routers/cv_convert.py (GET /info DB-first check)
tech_stack:
  added:
    - pymupdf>=1.25.0 (fitz — PDF page to PNG conversion)
    - python-multipart>=0.0.9 (required for FastAPI UploadFile support)
  patterns:
    - Two-pass LLM PDF parsing (OCR pass + structuring pass via Gemini)
    - asyncio.to_thread wrapping all blocking I/O (fitz, Gemini SDK)
    - BEGIN IMMEDIATE for all SQLite write transactions
    - Depends(get_current_user) auth on all CV endpoints
key_files:
  created:
    - core/cv_parser.py
    - backend/routers/cv.py
    - tests/test_cv_router.py
  modified:
    - backend/schemas.py
    - backend/main.py
    - backend/routers/cv_convert.py
    - pyproject.toml
    - uv.lock
decisions:
  - "Gemini 2.5 Flash-Lite for both OCR and structuring passes (D-01)"
  - "Inhouse GEMINI_API_KEY from .env for CV parsing — not per-user key (D-01)"
  - "PDF only — no DOCX support (D-01)"
  - "Store parsed CV as YAML text in users.base_cv_yaml column (D-02)"
  - "DB CV takes priority over YAML file in GET /cv/info (D-04)"
  - "python-multipart auto-added as missing dependency for UploadFile support (Rule 3)"
metrics:
  duration: 216s
  completed: "2026-04-07"
  tasks_completed: 2
  files_modified: 8
---

# Phase 1004 Plan 01: CV Parsing Backend — Summary

**One-liner:** Two-pass Gemini PDF parser (pymupdf images + OCR + structuring) with four auth-protected CRUD endpoints (upload/get/put/delete) backed by users.base_cv_yaml in SQLite.

## What Was Built

### Task 1: Install pymupdf + Create Two-Pass PDF Parser Module

Created `core/cv_parser.py` providing `parse_pdf_to_base_cv(pdf_bytes: bytes) -> BaseCV`:

- `_pdf_to_images()` — uses `fitz.open(stream=pdf_bytes, filetype="pdf")` and `page.get_pixmap(dpi=200)` to render each page as a PNG byte array
- `_ocr_images()` — Pass 1: sends all page PNGs to Gemini 2.5 Flash-Lite with OCR system instruction, returns raw extracted text
- `_structure_text()` — Pass 2: sends OCR text to Gemini 2.5 Flash-Lite with structuring prompt (reused from `cv_converter.py _CONVERT_PROMPT`), parses response to `BaseCV` with 3-attempt retry
- `parse_pdf_to_base_cv()` — async entry point, reads `GEMINI_API_KEY` from environment, wraps all three sync steps in `asyncio.to_thread`

Added `pymupdf>=1.25.0` to `pyproject.toml`.

### Task 2: CV CRUD Router + Upload Endpoint

Created `backend/routers/cv.py` with 4 endpoints:
- `POST /cv/upload` — validates PDF content_type and 10MB size limit, calls `parse_pdf_to_base_cv()`, saves YAML to DB
- `GET /cv/me` — queries `users.base_cv_yaml`, parses YAML and validates with `BaseCV.model_validate()`, returns `CvMeResponse`
- `PUT /cv/me` — validates request body against `BaseCV`, serializes to YAML, saves to DB
- `DELETE /cv/me` — sets `base_cv_yaml = NULL`

Updated `backend/schemas.py` with `CvUploadResponse` and `CvMeResponse` classes.

Updated `backend/main.py` to import and register `cv_router`.

Updated `backend/routers/cv_convert.py` `GET /info` to check DB first for `base_cv_yaml` (DB takes priority over YAML file fallback), adding `"source": "db"` or `"source": "file"` to the response.

Created `tests/test_cv_router.py` with 6 tests covering:
- GET /api/cv/me returns `has_cv=false` for new user
- PUT /api/cv/me saves CV
- GET /api/cv/me returns saved CV after PUT
- DELETE /api/cv/me removes CV
- PUT /api/cv/me with invalid data returns 422
- Full CRUD round trip

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added python-multipart dependency**
- **Found during:** Task 2 — first test run
- **Issue:** FastAPI raises `RuntimeError: Form data requires "python-multipart"` when a route declares `UploadFile` without this package installed
- **Fix:** Added `python-multipart>=0.0.9` to `pyproject.toml` dependencies and ran `uv sync`
- **Files modified:** `pyproject.toml`, `uv.lock`
- **Commit:** df3078c

## Verification Results

All four plan verifications passed:
1. `from core.cv_parser import parse_pdf_to_base_cv` — imports without error
2. `from backend.routers.cv import router; len(router.routes)` — shows 4 routes
3. `uv run pytest tests/test_cv_router.py -x -v` — 6/6 tests pass
4. `from backend.main import app; routes = [r.path for r in app.routes]` — confirms `/api/cv/upload`, `/api/cv/me` are registered

## Known Stubs

None — all endpoints are fully wired to the DB and parser pipeline.

## Self-Check: PASSED

- `/Users/nroo6394/Library/CloudStorage/OneDrive-SyscoCorporation/Documents/cv-maker/core/cv_parser.py` — FOUND
- `/Users/nroo6394/Library/CloudStorage/OneDrive-SyscoCorporation/Documents/cv-maker/backend/routers/cv.py` — FOUND
- `/Users/nroo6394/Library/CloudStorage/OneDrive-SyscoCorporation/Documents/cv-maker/tests/test_cv_router.py` — FOUND
- Commit `c4f74f0` (Task 1) — FOUND
- Commit `df3078c` (Task 2) — FOUND
