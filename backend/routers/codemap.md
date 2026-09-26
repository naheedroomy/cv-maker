# backend/routers/

## Responsibility

HTTP endpoint handlers for the CV Maker API, organized by domain concern. Each router file defines a FastAPI `APIRouter` with a prefix and is included into the `/api` parent router in `backend/main.py`. All routers share the `get_current_user` dependency for multi-tenant isolation.

## Design Patterns

- **RESTful routing**: Each router uses standard HTTP verbs: `GET` for reads, `POST` for creates/actions, `PUT` for updates, `PATCH` for partial updates, `DELETE` for removal.
- **Dependency injection**: Every protected endpoint takes `user: dict = Depends(get_current_user)` to extract the authenticated user. User-specific data is always filtered by `WHERE user_id=?`.
- **Fresh DB per request**: Each endpoint opens a new `aiosqlite.Connection` via `get_db()` and closes it in `finally`, avoiding stale handles.
- **Background execution**: Long-running operations (CV tailoring, cover letter generation) return HTTP 201/202 immediately and run the work in a background task via `schedule_background_task()`.
- **SSE streaming**: Real-time job status updates are pushed to the frontend via Server-Sent Events, with 30-second keep-alive timeouts and automatic cleanup on disconnect.
- **Pydantic contracts**: Request bodies and responses use Pydantic models from `backend.schemas`, with validation errors returning HTTP 422.

## Route / API Responsibilities

### `auth.py` — `prefix="/auth"`, tag `"auth"`

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth` | Exchange a Google ID token for an application JWT. Verifies the token with Google OAuth, upserts the user in the `users` table (INSERT ON CONFLICT DO UPDATE), and returns a signed HS256 JWT with 7-day expiry plus user profile. |

### `jobs.py` — `prefix="/jobs"`, tag `"jobs"`

| Method | Path | Description |
|---|---|---|
| `POST` | `/jobs` | **Create job.** Inserts a new job row with `status='pending'`, schedules `job_worker()` in the background, registers the task for cancellation support. Returns 201 with job ID. Checks for duplicate job links (409). |
| `GET` | `/jobs` | **List all jobs** for the authenticated user, ordered by `created_at DESC`. |
| `GET` | `/jobs/{id}` | **Get single job** by ID. Returns 404 if not found or owned by another user. |
| `DELETE` | `/jobs/{id}` | **Cancel job.** Cancels a `pending` or `running` job's background task. Returns 409 if already in a terminal state (`complete`/`failed`/`cancelled`). |
| `DELETE` | `/jobs/{id}/remove` | **Permanently delete job.** Cancels running tasks, removes the DB row, and deletes output files (`.pdf`, `.tex`). |
| `PATCH` | `/jobs/{id}/listing` | **Update job link/text.** Partial update of `job_link` and/or `job_text` fields. |
| `PATCH` | `/jobs/{id}/applied` | **Toggle applied status.** Flips the `applied` boolean and sets/clears `applied_at` timestamp. |
| `GET` | `/jobs/{id}/pdf` | **Download PDF** for a completed job. Returns raw PDF bytes. 404 if job is not `complete` or PDF path is null. |
| `GET` | `/jobs/{id}/pdf/{version}` | **Download historical PDF** from the CV version history (`cv_history_json`). |
| `POST` | `/jobs/{id}/regenerate` | **Re-run CV pipeline** on an existing job. Archives current CV into history, resets status to `pending`, clears outputs, and kicks off the worker. Optionally updates model, model_id, reasoning_effort, creativity_level (0–3), and user_notes. Preserves cover letter data. |
| `GET` | `/jobs/{id}/events` | **SSE event stream.** Subscribes to real-time status/completion events from the worker. If the job is already terminal, yields one event and closes. Uses 30-second keep-alive timeouts. |

### `cover_letter.py` — `prefix="/jobs"`, tag `"cover-letter"`

| Method | Path | Description |
|---|---|---|
| `POST` | `/jobs/{id}/cover-letter` | **Generate cover letter** in the background. Requires job to be `complete` with tailored CV data. Archives existing cover letter into history, clears `cover_letter_text` to signal "generating", and schedules `_cover_letter_worker()`. Returns 202. |
| `PUT` | `/jobs/{id}/cover-letter` | **Save edited cover letter** text back to the DB. |
| `GET` | `/jobs/{id}/cover-letter/pdf` | **Download cover letter as PDF.** Extracts candidate name from `tailored_cv_json` for the header. Renders via `core.cover_letter_renderer.render_cover_letter_pdf()` in a thread pool. |

### `settings.py` — `prefix="/settings"`, tag `"settings"`

| Method | Path | Description |
|---|---|---|
| `GET` | `/settings` | **Get all settings** for the authenticated user, merged with defaults. API keys are masked (shows `***` + last 4 chars). |
| `PUT` | `/settings` | **Update settings.** Accepts a partial payload; only provided fields are upserted into the `settings` table via `INSERT ... ON CONFLICT DO UPDATE`. |
| `POST` | `/settings/check-gemini-web` | **Test Gemini Web connectivity.** Reads the user's `gemini_web_psid` setting, initializes a `GeminiClient`, sends a test prompt, and reports success or error. |

### `cv.py` — `prefix="/cv"`, tag `"cv"`

| Method | Path | Description |
|---|---|---|
| `POST` | `/cv/upload` | **Upload PDF CV for parsing.** Accepts a `multipart/form-data` PDF (max 10 MB), validates content type, then runs `core.cv_parser.parse_pdf_to_base_cv()` (two-pass Gemini pipeline). Saves parsed BaseCV as YAML to `users.base_cv_yaml`. Returns success/failure with parsed CV data. |
| `GET` | `/cv/me` | **Get current user's saved CV** from the DB. Returns `has_cv=True` with the BaseCV dict, or `has_cv=False` if no CV is stored. |
| `PUT` | `/cv/me` | **Save edited CV.** Validates the request body against `BaseCV` (422 on invalid), serializes to YAML, and upserts into `users.base_cv_yaml`. |
| `DELETE` | `/cv/me` | **Remove saved CV.** Sets `users.base_cv_yaml` to NULL (reverts to YAML file fallback). |
| `POST` | `/cv/me/pdf` | **Render base CV as PDF.** Accepts CV data in the request body (so unsaved in-memory edits are included), converts `BaseCV` → `TailoredCV`, renders LaTeX and compiles PDF via the renderer pipeline. Returns PDF with `Content-Disposition: attachment`. |

### `cv_convert.py` — `prefix="/cv"`, tag `"cv"`

| Method | Path | Description |
|---|---|---|
| `GET` | `/cv/info` | **Return base CV info + full data.** Checks DB first (`users.base_cv_yaml`), then falls back to the YAML file (`core.data.load_base_cv()`). Returns `loaded: false` if no CV exists. |
| `POST` | `/cv/convert` | **Convert plain-text CV to YAML.** Runs `core.cv_converter.convert_cv_to_yaml()` in a thread pool (Claude CLI subprocess). On success, saves `base_cv.yaml` and returns the parsed data with YAML preview. Parse failures return `success=False` with error message (not HTTP errors). |

### `config.py` — `prefix="/config"`, tag `"config"`

| Method | Path | Description |
|---|---|---|
| `GET` | `/config` | **Return feature flags.** Reports which AI providers are available for the current user (based on DB-stored API keys, not server env vars). Also returns `google_client_id` for the frontend sign-in page. This endpoint is intentionally public — no 401 on missing token. |

## Data & Control Flow

### Job Lifecycle (jobs + worker)
```
POST /api/jobs
  → create_job() inserts row (status='pending')
  → schedule_background_task(job_worker())
  → job_worker acquires semaphore
    → pending → running (DB update + SSE event)
    → load base CV (DB then file)
    → run AI provider (thread pool)
    → render LaTeX (sync)
    → compile PDF (thread pool, latexmk)
    → save outputs to disk
    → running → complete (DB + SSE)
  → SSE subscribers receive events in real time
```

### Cover Letter Generation (cover_letter)
```
POST /api/jobs/{id}/cover-letter
  → Validates job is complete with tailored CV
  → Archives existing cover letter into cl_history_json
  → Clears cover_letter_text (signals "generating")
  → schedule_background_task(_cover_letter_worker())
    → Loads job data, base CV, and provider
    → Calls core.cover_letter.generate_cover_letter() (thread pool)
    → Saves result to DB
    → On failure: clears cover_letter_text back to NULL
  → Frontend polls GET /api/jobs/{id} to detect completion
```

### CV Upload + Parse (cv + cv_convert)
```
POST /api/cv/upload (PDF)
  → Validates content-type + size
  → core.cv_parser.parse_pdf_to_base_cv() (two-pass Gemini)
  → Saves YAML to users.base_cv_yaml

POST /api/cv/convert (plain text)
  → core.cv_converter.convert_cv_to_yaml() (Claude CLI)
  → save_base_cv() writes base_cv.yaml
```

### Auth Flow (auth)
```
POST /api/auth
  → verify_google_token(id_token) → Google OAuth verification
  → Upsert user in DB (INSERT ON CONFLICT DO UPDATE)
  → create_jwt(user_id, email, name) → HS256 token
  → Return { jwt, user }
  → get_current_user() decodes JWT on subsequent requests
```

## Integration Points

- `backend.auth.get_current_user` — injected into every endpoint for user isolation.
- `backend.db.get_db` — fresh DB connection opened per request.
- `backend.tasks.schedule_background_task` — long-running work is fire-and-forget.
- `backend.worker` (jobs router only) — `_job_tasks`, `_sse_queues`, and `job_worker` are directly imported for task lifecycle and SSE streaming.
- `backend.settings_cache.get_setting` — used in multiple routers (settings, config, cv, jobs) to read per-user configuration.
- `core.*` — domain logic package providing providers, models, renderer, parsers, and converters.

## Operational Notes

- **Cancellation contract**: `DELETE /api/jobs/{id}` calls `task.cancel()` on the asyncio task. The worker catches `CancelledError`, updates DB to `cancelled`, then **re-raises** (required by asyncio).
- **Duplicate detection**: `POST /api/jobs` checks for duplicate `job_link` per user and returns 409 if found.
- **Regenerate preserves history**: `POST /api/jobs/{id}/regenerate` archives the current CV into `cv_history_json` before clearing outputs, so old versions remain downloadable.
- **Cover letter history**: Similarly, generating a new cover letter archives the previous one into `cl_history_json`.
- **SSE cleanup**: The `finally` block in the SSE generator ensures the queue is removed from `_sse_queues` on disconnect, preventing memory leaks.
- **API key masking**: GET `/api/settings` masks all API keys as `***` + last 4 characters. The actual values are stored in plaintext in the DB.
- **Public config endpoint**: GET `/api/config` does not use `Depends(get_current_user)` — it accepts an optional `Authorization` header and extracts the user ID via best-effort JWT decoding. This allows the sign-in page (which has no token yet) to fetch `google_client_id`.
