# Multi-Base CVs & Enhanced Vision PDF Parser Specification

- **Date**: 2026-10-01
- **Status**: Approved
- **Scope**: Architectural

## 1. Problem Statement & Motivation

Currently, the CV Maker system only supports a single Base CV per user, stored in `users.base_cv_yaml` (falling back to `data/base_cv.yaml`). In practice, job seekers target distinct roles requiring specialized starting points (e.g., "Cloud Engineer base" vs. "Platform Engineer base" vs. "DevOps Engineer base"). When tailoring a CV, candidates need to pick the most relevant starting baseline.

Furthermore, the existing PDF upload parser:
1. Is hardcoded to `gemini-2.5-flash-lite` using a server-level `GEMINI_API_KEY` from `.env`, ignoring the user's personal API keys (configured in Settings).
2. Uses a low-accuracy quantized model and a two-pass OCR pipeline that frequently misinterprets or misspells crucial contact details (email addresses, candidate names, LinkedIn URLs, phone numbers, and dates).
3. Lacks support for other vision-capable models (e.g. Gemini 2.5 Flash / Pro, OpenAI GPT-4o / GPT-4o-mini).

## 2. Goals & Non-Goals

### Goals
- **Multiple Named Base CVs**: Allow users to create, view, edit, duplicate, rename, set as default, and delete multiple Base CVs.
- **Base CV Selection on Job Creation**: Enable candidates to choose which Base CV to tailor from on the job submission form, defaulting to their designated "Default" Base CV.
- **Traceability in Job Lifecycle**: Track which Base CV was used on the job detail page, and allow switching the Base CV when regenerating tailored CVs.
- **Multi-Provider Vision PDF Parser**: Allow PDF CV uploads to be parsed using either Gemini or OpenAI vision models, authenticated using the user's saved API keys in Settings.
- **High-Accuracy Hybrid Extraction**: Combine high-resolution page rendering (300 DPI) with native vector text extraction (`page.get_text()`) from the PDF to eliminate spelling and character errors on emails, names, URLs, and dates.

### Non-Goals
- Changing the structure of the underlying `BaseCV` or `TailoredCV` schemas (the core CV schema remains unchanged).
- Supporting non-PDF formats (DOCX remains out of scope for upload parsing).
- Sharing Base CVs between different user accounts.

---

## 3. Database Schema & Migration

### Schema Additions (`backend/db.py`)

A new table `base_cvs` is introduced:

```sql
CREATE TABLE IF NOT EXISTS base_cvs (
    id          TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    name        TEXT NOT NULL,
    cv_yaml     TEXT NOT NULL,
    is_default  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_base_cvs_user_id ON base_cvs(user_id);
```

The `jobs` table is extended with two columns:
- `base_cv_id TEXT REFERENCES base_cvs(id)`
- `base_cv_name TEXT`

### Migration Strategy
In `init_db()`:
1. `CREATE TABLE IF NOT EXISTS base_cvs ...`
2. Automatically check and apply column additions to `jobs` via `ALTER TABLE jobs ADD COLUMN base_cv_id TEXT` and `ALTER TABLE jobs ADD COLUMN base_cv_name TEXT` if they do not exist.
3. For every user in `users`:
   - If user has no entries in `base_cvs`:
     - If `users.base_cv_yaml` is not null, insert it into `base_cvs` with `name = 'Main Base CV'` and `is_default = 1`.
     - Otherwise, seed from `data/base_cv.yaml` as `'Main Base CV'` with `is_default = 1`.

---

## 4. Enhanced Vision PDF Parser Architecture (`core/cv_parser.py`)

### Hybrid Text & Vision Extraction
Standard PDFs have two data layers:
1. **Visual presentation** (layout, spacing, column order, font sizes).
2. **Native character streams** (exact vector strings for letters, numbers, punctuation).

The updated parser:
- Uses `pymupdf` (`fitz`) to extract:
  - Exact text stream via `page.get_text("text")`.
  - High-resolution page image via `page.get_pixmap(dpi=300).tobytes("png")`.
- Packages both into a multimodal prompt to the LLM:
  - The native text guarantees 100% exact character transcription of email addresses, names, URLs, phone numbers, and dates.
  - The page images provide layout understanding (e.g. multi-column layouts, sidebars, section hierarchy).

### Provider & Model Flexibility
- **Gemini Vision**: Supports `gemini-2.5-flash`, `gemini-2.5-pro` using the user's `gemini_api_key` (via `get_api_key("gemini_api_key", user_id)`), falling back to `GEMINI_API_KEY` from `.env`.
- **OpenAI Vision**: Supports `gpt-4o`, `gpt-4o-mini` using the user's `openai_api_key` (via `get_api_key("openai_api_key", user_id)`), sending base64-encoded image parts and text prompt.

---

## 5. API Contracts

### Base CV Endpoints (`backend/routers/cv.py`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/cv/list` | Returns `list[BaseCvMeta]` (`id`, `name`, `is_default`, `updated_at`, `created_at`). |
| `GET` | `/api/cv/{id}` | Returns `BaseCvDetail` (`id`, `name`, `is_default`, `cv: BaseCV`). |
| `POST` | `/api/cv` | Creates a new Base CV (`name`, `cv?: BaseCV`, `source_id?: str`, `is_default?: bool`). |
| `POST` | `/api/cv/upload` | Multipart upload: `file: UploadFile`, `name?: str`, `provider?: str`, `model?: str`. Uses vision parser with user API key. |
| `PUT` | `/api/cv/{id}` | Updates Base CV content (`name?: str`, `cv?: BaseCV`, `is_default?: bool`). Setting `is_default=true` unsets default on other CVs. |
| `DELETE` | `/api/cv/{id}` | Deletes Base CV. Rejects deletion if it is the user's only Base CV. If default is deleted, reassigns default to most recently updated CV. |
| `POST` | `/api/cv/{id}/pdf` | Compiles and returns PDF bytes for that specific Base CV with `Cache-Control: no-cache`. |
| `GET` | `/api/cv/me` | Backward-compatibility: returns the user's default Base CV. |
| `PUT` | `/api/cv/me` | Backward-compatibility: updates the user's default Base CV. |

### Job Endpoints (`backend/routers/jobs.py`)

- `POST /api/jobs`:
  - Request body `JobCreate` adds `base_cv_id?: str`.
  - If omitted, resolves user's default Base CV from `base_cvs`.
  - Saves `base_cv_id` and `base_cv_name` on the `jobs` row.
- `POST /api/jobs/{id}/regenerate`:
  - Request body `RegenerateRequest` adds `base_cv_id?: str`.
  - If provided, updates `base_cv_id` and `base_cv_name` on the job.
- Worker:
  - `job_worker` queries `base_cvs WHERE id = ?`. If missing or deleted, falls back to user default Base CV, then `data/base_cv.yaml`.

---

## 6. Frontend Architecture & User Experience

### 1. Store Updates (`frontend/src/stores/cvStore.ts`)
- State:
  - `baseCvs: BaseCvMeta[]` (list of all user Base CVs)
  - `activeCvId: string | null`
  - `activeCv: BaseCV | null`
  - `activeCvName: string`
  - `activeCvIsDefault: boolean`
- Actions:
  - `fetchBaseCvs()`: loads list, sets first or default as active if none selected.
  - `loadBaseCv(id)`: fetches full CV content for the selected CV.
  - `createBaseCv(name, { sourceId, file, model })`: creates blank, duplicates existing, or uploads PDF.
  - `saveActiveCv()`: saves changes to active CV.
  - `setDefaultBaseCv(id)`: marks CV as default.
  - `renameBaseCv(id, newName)`: updates CV name.
  - `deleteBaseCv(id)`: deletes CV and switches to default.

### 2. Base CV View (`frontend/src/views/BaseCvView.vue`)
- **Top Tab Bar**:
  - Horizontal pill/tab selector for each Base CV.
  - Default CV marked with a gold star (`★`) and "Default" tag.
  - Quick action buttons on active tab: `Rename`, `Set as Default`, `Duplicate`, `Delete`.
  - `+ New Base CV` button opening a creation modal with 3 choices:
    1. **Duplicate Current Base CV** (pre-fills with active CV data and appends "Copy").
    2. **Upload PDF** (includes model picker for Gemini / OpenAI vision models).
    3. **Start from Scratch** (clean blank template).
- **Editor Area**:
  - Mounts `<CvFormEditor>` for the selected `activeCv`.

### 3. Job Form View (`frontend/src/views/JobFormView.vue`)
- Adds a **Base CV Selector** directly above the Model Selector:
  - Dropdown showing all candidate's Base CVs: `Cloud Engineer base (Default)`, `Platform Engineer base`, etc.
  - Pre-selected with the user's default Base CV.

### 4. Job Detail & Regenerate Panel (`frontend/src/views/JobDetailView.vue` & `RegeneratePanel.vue`)
- Job Header shows: `Base: Cloud Engineer base`.
- In `RegeneratePanel.vue`, an optional dropdown lets the user switch the Base CV when regenerating a tailored CV.

---

## 7. Verification & Testing Plan

1. **Database & Migration Tests (`tests/test_db.py`)**:
   - Verify `base_cvs` table creation.
   - Verify automatic migration of existing `users.base_cv_yaml`.
   - Verify seeding fallback to `data/base_cv.yaml`.
2. **Base CV API Tests (`tests/test_cv_router.py`)**:
   - CRUD on `/api/cv/list`, `/api/cv/{id}`.
   - Duplicate existing CV via `source_id`.
   - Set as default / switch default.
   - Guard against deleting the only Base CV.
3. **Enhanced PDF Parser Tests (`tests/test_cv_parser.py`)**:
   - Hybrid native text + vision image extraction.
   - Gemini vision parser with mock API key.
   - OpenAI vision parser with mock API key.
   - Exact email and name transcription without typos.
4. **Job Lifecycle Integration Tests (`tests/test_jobs_router.py`)**:
   - Submitting job with specific `base_cv_id`.
   - Submitting job with omitted `base_cv_id` defaulting correctly.
   - Regenerating with switched `base_cv_id`.
5. **Frontend Verification**:
   - `npm run build` (`vue-tsc --build` + `vite build`) type checks clean.
