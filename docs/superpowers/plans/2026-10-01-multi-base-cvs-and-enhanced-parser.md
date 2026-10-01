# Multi-Base CVs & Enhanced Vision PDF Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement multiple named Base CVs per user (allowing selection during job creation/regeneration) and an enhanced vision PDF parser with hybrid vector text + high-res image extraction supporting user-configured Gemini and OpenAI models.

**Architecture:**
- Create `base_cvs` SQLite table with automatic migration of existing `users.base_cv_yaml` and `data/base_cv.yaml` fallback.
- Extend `core/cv_parser.py` with hybrid PyMuPDF text stream extraction (`page.get_text()`) + 300 DPI images, supporting Gemini and OpenAI vision models authenticated with user API keys from settings.
- Implement REST API for Base CV CRUD and link jobs to `base_cv_id` and `base_cv_name`.
- Build tabbed Base CV manager UI, vision model upload picker, and job creation/regeneration Base CV selectors in Vue 3.

**Tech Stack:** Python 3.13, FastAPI, aiosqlite, PyMuPDF (fitz), google-genai, openai, Vue 3, TypeScript, Pinia, Vite.

**Spec:** `docs/superpowers/specs/2026-10-01-multi-base-cvs-and-enhanced-parser-design.md`

## Global Constraints
- Python deps: `uv sync` (project uses `uv` + hatchling).
- Backend dev/tests: `uv run pytest` (`pytest-asyncio` auto mode). Line length: 100 characters.
- SQLite connections: WAL mode, `busy_timeout=5000`, `foreign_keys=ON`, `BEGIN IMMEDIATE` for writes.
- Multi-tenancy: per-user `user_id` on all queries, anonymous user id = 1.
- Frontend: `npm run build` runs `vue-tsc --build` before `vite build`.

---

### Task 1: Database Schema & Migration for `base_cvs` and `jobs`

**Files:**
- Modify: `backend/db.py:24-150`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces: `base_cvs` table (`id`, `user_id`, `name`, `cv_yaml`, `is_default`, `created_at`, `updated_at`), `jobs.base_cv_id`, `jobs.base_cv_name`.
- Consumes: `users` table, `data/base_cv.yaml`.

- [ ] **Step 1: Write failing tests in `tests/test_db.py`**

Add tests for:
1. `test_base_cvs_table_created`: `init_db()` creates `base_cvs` table and adds `base_cv_id`, `base_cv_name` to `jobs`.
2. `test_base_cvs_migrates_existing_user_cv`: when a user has `base_cv_yaml`, `init_db()` creates a default entry in `base_cvs` named "Main Base CV" with `is_default=1`.
3. `test_base_cvs_seeds_from_yaml_if_empty`: when a user has no CV, `init_db()` seeds from `data/base_cv.yaml` as "Main Base CV" with `is_default=1`.

```python
async def test_base_cvs_schema_and_migration(tmp_path: Path):
    test_db = tmp_path / "test.db"
    await init_db(test_db)
    db = await get_db(test_db)
    try:
        # Check base_cvs table exists
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='base_cvs'")
        row = await cursor.fetchone()
        assert row is not None

        # Check default seeded CV for user 1
        cursor = await db.execute("SELECT * FROM base_cvs WHERE user_id = 1")
        cv_rows = await cursor.fetchall()
        assert len(cv_rows) == 1
        assert cv_rows[0]["name"] == "Main Base CV"
        assert cv_rows[0]["is_default"] == 1

        # Check jobs table columns
        cursor = await db.execute("PRAGMA table_info(jobs)")
        cols = {r["name"] for r in await cursor.fetchall()}
        assert "base_cv_id" in cols
        assert "base_cv_name" in cols
    finally:
        await db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db.py -k "test_base_cvs_schema_and_migration" -v`
Expected: FAIL (table `base_cvs` does not exist).

- [ ] **Step 3: Implement schema and migration in `backend/db.py`**

In `backend/db.py`:
1. Add `base_cvs` table creation to `_SCHEMA`:
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
2. In `init_db()`, after table creation:
   - Check `PRAGMA table_info(jobs)` and run `ALTER TABLE jobs ADD COLUMN base_cv_id TEXT` and `ALTER TABLE jobs ADD COLUMN base_cv_name TEXT` if missing.
   - For all users in `users`, check if they have rows in `base_cvs`. If none:
     - If `user['base_cv_yaml']` is present, insert into `base_cvs` with UUID, `name='Main Base CV'`, `is_default=1`.
     - Else if `data/base_cv.yaml` exists, insert contents into `base_cvs` with UUID, `name='Main Base CV'`, `is_default=1`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/db.py tests/test_db.py
git commit -m "feat(db): add base_cvs table, job columns, and auto-migration"
```

---

### Task 2: Enhanced Vision PDF Parser with Hybrid Text Extraction & Multi-Provider Support

**Files:**
- Modify: `core/cv_parser.py`
- Test: `tests/test_cv_parser.py`

**Interfaces:**
- Produces: `async def parse_pdf_to_base_cv(pdf_bytes: bytes, provider: str = "gemini", model: str | None = None, api_key: str | None = None) -> BaseCV`
- Consumes: `fitz` (PyMuPDF), `google-genai`, `openai`, `BaseCV`.

- [ ] **Step 1: Write failing tests in `tests/test_cv_parser.py`**

Test:
1. `test_extract_hybrid_pdf_content`: verifies `_extract_pdf_pages(pdf_bytes)` extracts high-res PNG images and native vector text from PDF pages.
2. `test_parse_pdf_gemini_vision`: verifies Gemini vision parse with mocked client and prompt containing native text and image parts.
3. `test_parse_pdf_openai_vision`: verifies OpenAI vision parse with mocked OpenAI client sending image data URLs and text.
4. `test_parse_pdf_missing_key_raises`: raises RuntimeError if requested provider key is empty.

```python
async def test_extract_hybrid_pdf_content(sample_pdf_bytes: bytes):
    pages = _extract_pdf_pages(sample_pdf_bytes, dpi=300)
    assert len(pages) > 0
    assert "images" in pages[0]
    assert "text" in pages[0]
    assert len(pages[0]["images"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cv_parser.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement enhanced parser in `core/cv_parser.py`**

1. Update `_extract_pdf_pages(pdf_bytes: bytes, dpi: int = 300) -> list[dict]`:
   - For each page in `fitz.open(stream=pdf_bytes, filetype="pdf")`:
     - `page_text = page.get_text("text").strip()`
     - `pixmap = page.get_pixmap(dpi=dpi)`
     - `page_img = pixmap.tobytes("png")`
     - Append `{"image": page_img, "text": page_text}`.
2. Update structuring prompt to include `EXACT EXTRACTED TEXT FROM PDF (Verbatim characters for email, name, URLs, dates)`:
   - Instructs model: "Cross-reference the layout image with the exact text stream. Use the exact email address, name, URLs, and phone number from the text stream without spelling modifications."
3. In `parse_pdf_to_base_cv(pdf_bytes, provider="gemini", model=None, api_key=None)`:
   - If `provider == "openai"`:
     - Use `openai.AsyncOpenAI(api_key=api_key)`.
     - Model default: `gpt-4o`.
     - Format contents with `type: "image_url"` (base64 data URL) and `type: "text"` containing native page text.
   - If `provider == "gemini"`:
     - Use `google.genai.Client(api_key=api_key)`.
     - Model default: `gemini-2.5-flash` (replacing `gemini-2.5-flash-lite`).
     - Pass image parts + text part.
   - Parse response JSON into `BaseCV.model_validate(json_data)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cv_parser.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/cv_parser.py tests/test_cv_parser.py
git commit -m "feat(parser): add hybrid native text + high-res vision PDF parsing for Gemini and OpenAI"
```

---

### Task 3: Multi-Base CV API Endpoints and Schemas

**Files:**
- Modify: `backend/schemas.py:45-80`
- Modify: `backend/routers/cv.py:1-218`
- Test: `tests/test_cv_router.py`

**Interfaces:**
- Produces:
  - `GET /api/cv/list` -> `list[BaseCvMeta]`
  - `GET /api/cv/{id}` -> `BaseCvDetail`
  - `POST /api/cv` -> `BaseCvDetail`
  - `POST /api/cv/upload` (with `name`, `provider`, `model`, `api_key`) -> `CvUploadResponse`
  - `PUT /api/cv/{id}` -> `BaseCvDetail`
  - `DELETE /api/cv/{id}` -> `dict`
  - `POST /api/cv/{id}/pdf` -> `Response(application/pdf)`
- Consumes: `backend.db.get_db`, `backend.settings_cache.get_api_key`, `core.cv_parser.parse_pdf_to_base_cv`.

- [ ] **Step 1: Write failing tests in `tests/test_cv_router.py`**

Add tests for:
1. `test_list_base_cvs`: returns array with default CV.
2. `test_create_and_get_base_cv`: creates a named CV and retrieves it by ID.
3. `test_duplicate_base_cv`: creates a copy of an existing Base CV via `source_id`.
4. `test_set_default_base_cv`: updates `is_default=true` and unsets previous default.
5. `test_delete_base_cv_guard_last_one`: returns 400 when attempting to delete the only remaining Base CV.
6. `test_upload_base_cv_with_name_and_model`: parses PDF using user key and creates named Base CV.
7. `test_download_base_cv_by_id_pdf`: returns PDF bytes with `Cache-Control: no-cache`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cv_router.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement schemas and endpoints**

1. In `backend/schemas.py`:
   - `BaseCvMeta`: `id: str`, `name: str`, `is_default: bool`, `created_at: str`, `updated_at: str`.
   - `BaseCvDetail`: `id: str`, `name: str`, `is_default: bool`, `created_at: str`, `updated_at: str`, `cv: dict`.
   - `BaseCvCreate`: `name: str`, `cv: dict | None = None`, `source_id: str | None = None`, `is_default: bool = False`.
   - `BaseCvUpdate`: `name: str | None = None`, `cv: dict | None = None`, `is_default: bool | None = None`.
2. In `backend/routers/cv.py`:
   - Implement `GET /api/cv/list`.
   - Implement `GET /api/cv/{id}`.
   - Implement `POST /api/cv`: if `source_id`, copy `cv_yaml` from source. If `is_default`, unset other defaults in transaction.
   - Update `POST /api/cv/upload`:
     - Form parameters: `file: UploadFile`, `name: str = "Uploaded Base CV"`, `provider: str = "gemini"`, `model: str | None = None`.
     - Resolve key: `key_name = "openai_api_key" if provider == "openai" else "gemini_api_key"`, `api_key = await get_api_key(key_name, user["id"])`.
     - Call `await parse_pdf_to_base_cv(pdf_bytes, provider=provider, model=model, api_key=api_key)`.
     - Insert into `base_cvs`, set as default if user has no other CVs.
   - Implement `PUT /api/cv/{id}`: update name, CV, or default.
   - Implement `DELETE /api/cv/{id}`: check if count == 1 -> raise 400. If deleting default, assign `is_default=1` to the next available CV.
   - Implement `POST /api/cv/{id}/pdf`: compile PDF with `Cache-Control: no-cache`.
   - Keep `/api/cv/me` (GET/PUT/DELETE) forwarding to the user's default CV.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cv_router.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/schemas.py backend/routers/cv.py tests/test_cv_router.py
git commit -m "feat(api): add multi-base CV CRUD, PDF compilation, and enhanced upload endpoint"
```

---

### Task 4: Job Creation & Worker Integration with Selected Base CV

**Files:**
- Modify: `backend/schemas.py`
- Modify: `backend/routers/jobs.py`
- Modify: `backend/worker.py`
- Test: `tests/test_jobs_router.py`

**Interfaces:**
- Produces: `jobs.base_cv_id`, `jobs.base_cv_name` populated on `create_job` and preserved through `job_worker`.
- Consumes: `base_cvs` table in `backend/worker.py`.

- [ ] **Step 1: Write failing tests in `tests/test_jobs_router.py`**

Add tests:
1. `test_create_job_with_specific_base_cv`: submitting `base_cv_id` associates job with that specific Base CV's ID and name.
2. `test_create_job_defaults_to_default_base_cv`: submitting without `base_cv_id` selects default Base CV.
3. `test_worker_uses_selected_base_cv`: worker loads the exact `cv_yaml` matching `base_cv_id`.
4. `test_regenerate_allows_switching_base_cv`: `POST /api/jobs/{id}/regenerate` with new `base_cv_id` updates base CV name and runs worker with it.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_jobs_router.py -k "base_cv" -v`
Expected: FAIL.

- [ ] **Step 3: Implement job and worker integration**

1. In `backend/schemas.py`:
   - `JobCreate`: add `base_cv_id: str | None = None`.
   - `JobResponse`: add `base_cv_id: str | None = None`, `base_cv_name: str | None = None`.
   - `RegenerateRequest`: add `base_cv_id: str | None = None`.
2. In `backend/routers/jobs.py`:
   - `create_job`:
     - If `body.base_cv_id`: query `base_cvs WHERE id=? AND user_id=?`. If not found, raise 404.
     - Else: query `base_cvs WHERE user_id=? AND is_default=1 LIMIT 1` (fallback to first row).
     - Store `base_cv_id` and `base_cv_name` in DB `INSERT INTO jobs`.
     - Pass `base_cv_id` to `job_worker`.
   - `regenerate_job`:
     - If `body.base_cv_id`: fetch name and update `base_cv_id`, `base_cv_name` in `jobs`.
     - Pass `base_cv_id` to `job_worker`.
   - `_row_to_response`: include `base_cv_id` and `base_cv_name`.
3. In `backend/worker.py`:
   - Add `base_cv_id: str | None = None` parameter to `job_worker`.
   - In `job_worker`:
     - If `base_cv_id`: load `cv_yaml` from `base_cvs WHERE id=?`.
     - Else: query `base_cvs WHERE user_id=? AND is_default=1 LIMIT 1`.
     - Fallback: `data/base_cv.yaml`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_jobs_router.py -k "base_cv" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/schemas.py backend/routers/jobs.py backend/worker.py tests/test_jobs_router.py
git commit -m "feat(jobs): support selecting and tracking Base CV in job creation, worker, and regeneration"
```

---

### Task 5: Frontend Pinia CV Store & Types

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/stores/cvStore.ts`
- Modify: `frontend/src/stores/jobStore.ts`

**Interfaces:**
- Produces: `useCvStore` state (`baseCvs`, `activeCvId`, `activeCv`, `activeCvName`, `activeCvIsDefault`) and actions (`fetchBaseCvs`, `selectBaseCv`, `createBaseCv`, `saveActiveCv`, `deleteBaseCv`, `setDefaultBaseCv`, `renameBaseCv`, `downloadBaseCvPdf`).
- Consumes: `/api/cv/list`, `/api/cv/{id}`, `/api/cv/upload`.

- [ ] **Step 1: Update TypeScript types in `frontend/src/types/index.ts`**

Define:
```ts
export interface BaseCvMeta {
  id: string
  name: string
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface BaseCvDetail extends BaseCvMeta {
  cv: BaseCV
}
```
Update `JobResponse` and `JobCreatePayload` with `base_cv_id?: string` and `base_cv_name?: string`.

- [ ] **Step 2: Update `cvStore.ts` for multi-CV management**

Implement reactive state:
- `baseCvs = ref<BaseCvMeta[]>([])`
- `activeCvId = ref<string | null>(null)`
- `activeCv = ref<BaseCV | null>(null)`
- `activeCvName = ref<string>('')`
- `activeCvIsDefault = ref<boolean>(false)`

Implement actions:
- `fetchBaseCvs()`: calls `/api/cv/list`. If `activeCvId` is unset, selects default or first.
- `selectBaseCv(id: string)`: calls `/api/cv/${id}`, updates `activeCvId`, `activeCv`, `activeCvName`, `activeCvIsDefault`.
- `createBaseCv(name: string, options?: { sourceId?: string; file?: File; provider?: string; model?: string })`: creates blank, duplicate, or uploads PDF.
- `saveActiveCv()`: PUT `/api/cv/${activeCvId.value}` with `{ name: activeCvName.value, cv: activeCv.value }`.
- `setDefaultBaseCv(id: string)`: PUT `/api/cv/${id}` with `{ is_default: true }`.
- `renameBaseCv(id: string, newName: string)`: PUT `/api/cv/${id}` with `{ name: newName }`.
- `deleteBaseCv(id: string)`: DELETE `/api/cv/${id}`, re-fetches list and selects new default.
- `downloadBaseCvPdf(id: string)`: POST `/api/cv/${id}/pdf` with cache buster.

- [ ] **Step 3: Update `jobStore.ts`**

Update `submitJob` and `regenerateJob` to accept `base_cv_id?: string`.

- [ ] **Step 4: Run frontend type-check**

Run: `cd frontend && npm run build`
Expected: PASS with 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/stores/cvStore.ts frontend/src/stores/jobStore.ts
git commit -m "feat(frontend): add multi-base CV store actions and types"
```

---

### Task 6: Frontend Base CV Manager with Tabbed Selector & Creation Modal

**Files:**
- Modify: `frontend/src/views/BaseCvView.vue`
- Modify: `frontend/src/components/PdfDropZone.vue`

**Interfaces:**
- Produces: Tabbed UI selector for Base CVs with `Set Default`, `Rename`, `Duplicate`, `Delete`, and `+ New Base CV` modal with vision model selection.
- Consumes: `cvStore`.

- [ ] **Step 1: Update `PdfDropZone.vue` to include model picker**

In `frontend/src/components/PdfDropZone.vue`:
- Add dropdown for vision models:
  - Gemini: `gemini-2.5-flash` (Default), `gemini-2.5-pro`
  - OpenAI: `gpt-4o`, `gpt-4o-mini`
- Emit selected provider and model along with the file on `@upload`.

- [ ] **Step 2: Update `BaseCvView.vue`**

In `frontend/src/views/BaseCvView.vue`:
1. Top Bar:
   - Tab list rendering `baseCvs`:
     - Clicking tab calls `selectBaseCv(item.id)`.
     - Badge `★ Default` on the default Base CV.
   - Quick action buttons for active CV:
     - `Set as Default` (visible if `!activeCvIsDefault`)
     - `Rename` (inline prompt / modal)
     - `Duplicate` (calls `createBaseCv(activeCvName + ' Copy', { sourceId: activeCvId })`)
     - `Delete` (disabled if `baseCvs.length <= 1`, with confirmation)
   - `+ New Base CV` button opening a modal with 3 cards:
     - **Duplicate Active Base CV**: clones current CV.
     - **Upload PDF**: renders `PdfDropZone` with vision model picker and custom CV name input.
     - **Start Blank**: creates empty template with user-specified name.
2. Main Body:
   - Renders `<CvFormEditor>` bound to `activeCv`, with title `${activeCvName}` and save label "Save Base CV".
   - Top action buttons: `Download PDF` (calls `downloadBaseCvPdf(activeCvId)`), `Save Base CV`.

- [ ] **Step 3: Run frontend build to verify compilation**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/BaseCvView.vue frontend/src/components/PdfDropZone.vue
git commit -m "feat(ui): add tabbed Base CV switcher, creation modal, and vision model upload picker"
```

---

### Task 7: Frontend Job Creation & Regeneration Base CV Selector

**Files:**
- Modify: `frontend/src/views/JobFormView.vue`
- Modify: `frontend/src/views/JobDetailView.vue`
- Modify: `frontend/src/components/RegeneratePanel.vue`

**Interfaces:**
- Produces: Base CV selector on job form and regenerate panel, and `Base: <name>` badge in job detail header.
- Consumes: `cvStore.baseCvs`, `jobStore.currentJob.base_cv_name`.

- [ ] **Step 1: Add Base CV selector to `JobFormView.vue`**

In `frontend/src/views/JobFormView.vue`:
1. Import and mount `cvStore.fetchBaseCvs()` on mount.
2. Add a `selectedBaseCvId` ref, defaulting to `cvStore.baseCvs.find(c => c.is_default)?.id || cvStore.baseCvs[0]?.id`.
3. Add a form field above the Model Selector:
   ```html
   <div class="field">
     <label for="base-cv-select" class="field-label">Base CV</label>
     <select id="base-cv-select" v-model="selectedBaseCvId" class="field-select">
       <option v-for="cv in cvStore.baseCvs" :key="cv.id" :value="cv.id">
         {{ cv.name }} {{ cv.is_default ? '(Default)' : '' }}
       </option>
     </select>
   </div>
   ```
4. Pass `base_cv_id: selectedBaseCvId.value` into `store.submitJob(...)`.

- [ ] **Step 2: Update `JobDetailView.vue` & `RegeneratePanel.vue`**

In `frontend/src/views/JobDetailView.vue`:
- In the job header badges, display:
  ```html
  <span v-if="currentJob.base_cv_name" class="model-badge">Base: {{ currentJob.base_cv_name }}</span>
  ```

In `frontend/src/components/RegeneratePanel.vue`:
- Add optional Base CV dropdown selector to pick a different Base CV when regenerating.
- Pass `baseCvId` event argument to `@regenerate`.
- `JobDetailView.vue` passes `baseCvId` to `store.regenerateJob(...)`.

- [ ] **Step 3: Run frontend build to verify compilation**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/JobFormView.vue frontend/src/views/JobDetailView.vue frontend/src/components/RegeneratePanel.vue
git commit -m "feat(ui): add Base CV selector on job creation form and regenerate panel"
```

---

### Task 8: End-to-End Verification & Full Test Suite

**Files:**
- Test: all test files (`tests/`)

- [ ] **Step 1: Run full pytest test suite**

Run: `uv run pytest`
Expected: All tests pass.

- [ ] **Step 2: Run ruff linter check**

Run: `uv run ruff check .`
Fix any linting or formatting issues in modified files.

- [ ] **Step 3: Run frontend production build**

Run: `cd frontend && npm run build`
Expected: Clean build with 0 type errors.

- [ ] **Step 4: Final commit and push**

Push branch and create PR for deployment to VPS.
