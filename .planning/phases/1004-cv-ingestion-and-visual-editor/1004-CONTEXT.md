# Phase 1004: CV Ingestion & Visual Editor - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Let users upload a PDF of their existing CV, have AI parse it into the structured BaseCV model, then view and edit their parsed CV in a sectioned visual editor. Deliver:
1. Backend: PDF upload endpoint (`POST /api/cv/upload`), LLM-based parsing via Gemini 2.5 Flash-Lite (two-pass: images→OCR text→BaseCV JSON)
2. Backend: CV CRUD endpoints (`GET /api/cv/me`, `PUT /api/cv/me`, `DELETE /api/cv/me`) backed by `users.base_cv_yaml` column
3. Frontend: Replace `BaseCvView.vue` with a visual sectioned editor (Work Experience, Education, Skills, Summary, Contact) with inline editing
4. Frontend: File upload drop zone on the editor page with parsing progress
5. Pipeline integration: load CV from DB first, fall back to YAML file if NULL

This phase does **not** include: DOCX upload (PDF only), multiple CV variants per user, CV version history, or template selection.

</domain>

<decisions>
## Implementation Decisions

### D-01: CV Parsing — LLM-Based with Gemini
- **No programmatic PDF extraction library** — use Gemini 2.5 Flash-Lite as the LLM for both OCR and structuring
- **PDF to images**: `pymupdf` (`fitz`) — `page.get_pixmap()` converts each page to PNG. Pure Python, no system deps.
- **Two-pass pipeline**:
  - Pass 1 (OCR): Send page images to Gemini 2.5 Flash-Lite → get structured text
  - Pass 2 (Structuring): Send OCR text to Gemini 2.5 Flash-Lite → get BaseCV JSON validated against Pydantic model
- **Both passes use `gemini-2.5-flash-lite`** — same model for OCR and structuring
- **API key**: Use `GEMINI_API_KEY` env var (server-side inhouse key) — since per-user API keys are now in the DB, the `.env` key is free for inhouse use like CV parsing
- **PDF only** — no DOCX support. Most CVs are PDF. Simplifies the pipeline.

### D-02: CV Storage & API
- Store parsed CV as YAML text in `users.base_cv_yaml` column (exists since Phase 1002 D-07)
- `GET /api/cv/me` — returns parsed BaseCV JSON for the authenticated user (from `base_cv_yaml`)
- `PUT /api/cv/me` — saves updated BaseCV JSON as YAML to `users.base_cv_yaml`
- `DELETE /api/cv/me` — sets `base_cv_yaml` to NULL (reverts to YAML file fallback)
- `POST /api/cv/upload` — accepts PDF file, runs two-pass Gemini parsing, saves result to DB, returns parsed BaseCV JSON

### D-03: Visual CV Editor Frontend
- **Replace `BaseCvView.vue`** — repurpose as the editable CV editor with upload + sections (same `/base-cv` route)
- **Inline editing with collapsible sections** — each section (Work Experience, Education, Skills, Summary, Contact) is a collapsible panel
- **Add/edit/delete per entry** — work experience entries, education entries, skills, certifications
- **Drop zone + file picker** on the editor page for PDF upload. Shows parsing progress with spinner.
- **Data flow**: `GET /api/cv/me` → edit in Vue reactive state → `PUT /api/cv/me` on "Save CV" button click

### D-04: Pipeline Integration
- `pipeline_runner.py` (or `worker.py`) loads CV from DB: if `users.base_cv_yaml` is not NULL, parse into BaseCV. If NULL, fall back to `data/base_cv.yaml` file.
- Sidebar shows "CV: Uploaded" or "CV: Not uploaded" linking to `/base-cv` editor page
- "Remove CV" button on editor page sets `base_cv_yaml` to NULL
- Existing `CvConverterView` (text-paste converter) stays as-is — alternative input method

### Claude's Discretion
- Exact collapsible section UI styling (accordion vs cards)
- pymupdf DPI setting for page rendering (150-300 DPI range)
- Gemini prompt design for OCR pass and structuring pass
- Whether to show a parsed CV diff/preview before saving
- Error handling UX for failed PDF parsing (retry button, error message)
- Whether to add loading skeleton states during CV fetch

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### DB Schema (Phase 1002)
- `backend/db.py` — `users` table with `base_cv_yaml TEXT` column, `get_db()`, `ANONYMOUS_USER_ID`

### Auth (Phase 1003)
- `backend/auth.py` — `get_current_user()` FastAPI dependency for JWT user extraction
- `frontend/src/utils/apiFetch.ts` — Authenticated fetch wrapper

### Existing CV Code
- `core/models.py` — `BaseCV` Pydantic model (the target schema for parsing)
- `core/data.py` — `load_base_cv()`, `DEFAULT_CV_PATH` — current YAML file loader
- `core/cv_converter.py` — Existing text-paste CV converter (reusable patterns)
- `frontend/src/views/BaseCvView.vue` — Current read-only CV preview (to be replaced with editor)
- `frontend/src/views/CvConverterView.vue` — Text-paste converter (keep as-is)

### Gemini Provider
- `core/providers/gemini_provider.py` — Existing Gemini provider (reusable client patterns)
- `core/providers/__init__.py` — `get_provider()` async factory

### Pipeline
- `backend/worker.py` — Background job worker (needs DB CV loading)
- `backend/pipeline_runner.py` — Pipeline orchestration

### Requirements
- `.planning/REQUIREMENTS.md` CVED-01 through CVED-06

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/models.py` `BaseCV` — the Pydantic model that defines the CV structure. The parsing pipeline must produce valid BaseCV JSON.
- `core/cv_converter.py` `convert_cv_to_yaml()` — existing text→BaseCV converter using AI. Reusable prompt patterns.
- `core/providers/gemini_provider.py` — Gemini client initialization pattern with `genai.Client`
- `frontend/src/components/CvPreview.vue` — Read-only CV preview component (can be used alongside editor)

### Established Patterns
- FastAPI endpoints use `Depends(get_current_user)` for auth (Phase 1003)
- Frontend uses `apiFetch()` for authenticated API calls
- Pinia stores use setup-store pattern with `storeToRefs`
- Background processing uses `asyncio.to_thread()` for blocking calls

### Integration Points
- `backend/main.py` — Register new CV router
- `backend/worker.py` — Load base CV from DB instead of file
- `frontend/src/components/AppSidebar.vue` — Add CV status indicator
- `frontend/src/router/index.ts` — `/base-cv` route already exists

</code_context>

<specifics>
## Specific Ideas

- User explicitly wants LLM-based OCR over programmatic extraction — "LLMs are very superior to programmatic PDF extraction"
- Inhouse GEMINI_API_KEY is OK for CV parsing since per-user keys are in DB now, .env key is free for inhouse use
- PDF only, no DOCX — simplifies pipeline significantly
- Two-pass Gemini (OCR → structuring) both using gemini-2.5-flash-lite
- Limited user base means inhouse API costs are acceptable

</specifics>

<deferred>
## Deferred Ideas

- DOCX upload support (PDF covers most cases)
- Multiple CV variants per user
- CV version history / undo
- Parsed CV diff preview before saving

</deferred>

---

*Phase: 1004-cv-ingestion-and-visual-editor*
*Context gathered: 2026-04-07 via smart discuss*
