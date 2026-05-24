# backend/

## Responsibility

The FastAPI backend for CV Maker — a multi-tenant REST API that orchestrates AI-powered CV tailoring, cover letter generation, PDF rendering, and user authentication. It serves as the bridge between the Vue SPA frontend and the `core/` domain logic (providers, renderer, parsers). All state is persisted in a single SQLite database (`backend/cv_maker.db`) using WAL mode.

## Key Files & Symbols

| File | Purpose |
|---|---|
| `main.py` | App entry point. Creates the FastAPI instance, registers the lifespan (DB init), mounts CORS middleware, assembles the `/api` router from all sub-routers, and serves the Vue SPA static files when `frontend/dist/` exists. |
| `db.py` | SQLite schema and connection helpers. Defines the multi-tenant schema (`users`, `jobs`, `settings` tables), the `ANONYMOUS_USER_ID=1` constant, `init_db()` for table creation + migration + seeding, and `get_db()` for opening a fresh connection with WAL + busy_timeout + foreign_keys enabled. |
| `auth.py` | Google OAuth 2.0 token verification and JWT issuance/decoding. `verify_google_token()` validates ID tokens against Google. `create_jwt()`/`decode_jwt()` issue/read HS256 tokens with 7-day expiry. `get_current_user()` is a FastAPI `Depends()` with a dev-mode fallback: returns the anonymous local user (id=1) when `GOOGLE_CLIENT_ID` is not configured. |
| `worker.py` | The background pipeline executor. `job_worker()` drives status transitions (`pending` → `running` → `complete`/`failed`/`cancelled`), loads the base CV (DB first, then YAML file), runs the AI provider, renders LaTeX, compiles PDF via latexmk, saves output files, and pushes SSE events. Concurrency is limited to 5 via `asyncio.Semaphore(5)`. |
| `schemas.py` | Pydantic request/response contracts for jobs, CVs, and cover letters. Defines `JobCreate`, `JobResponse`, `CvConvertRequest/Response`, `CoverLetterRequest/Response`, `CvUploadResponse`, and `CvMeResponse`. |
| `tasks.py` | GC-safe background task registry. `schedule_background_task()` wraps `asyncio.create_task()` and stores the task in a module-level `set` so the garbage collector does not collect live tasks. Tasks self-remove on completion. |
| `settings_cache.py` | Per-user settings lookup with default fallbacks. `get_setting()` queries the `settings` table for the given user, falling back to hardcoded `_DEFAULTS`. `get_api_key()` adds an env-var fallback layer (DB > env > empty). Default model names, API keys, `cv_filename`, and Gemini Web credentials are managed here. |
| `pipeline_runner.py` | Async wrappers for the synchronous `core` pipeline and renderer. `run_provider_async()` and `render_pdf_async()` use `asyncio.to_thread()` to offload blocking `subprocess.run` calls to the thread pool, preventing event-loop stalls. |

## Design Patterns

- **Lifespan pattern**: `main.py` uses FastAPI's `@asynccontextmanager` lifespan to run `init_db()` and seed the base CV on startup.
- **Dependency injection**: `get_current_user()` is injected into every protected endpoint via `Depends()`. It extracts the user from the `Authorization: Bearer <jwt>` header.
- **Dev-mode auth fallback**: When `GOOGLE_CLIENT_ID` is not set (local development), all endpoints default to the anonymous local user (`id=1`). In production, missing tokens return 401.
- **Per-request DB connections**: Every endpoint opens a fresh `aiosqlite` connection via `get_db()` and closes it in a `finally` block. Long-running workers also use fresh connections for each DB transaction to avoid stale connections.
- **BEGIN IMMEDIATE**: All write transactions use `BEGIN IMMEDIATE` to avoid SQLITE_BUSY under concurrent access.
- **Background task registry**: Tasks scheduled via `schedule_background_task()` are stored in a module-level `set` with `add_done_callback(self.discard)` to prevent GC.
- **SSE event queues**: `worker.py` maintains a dict of `asyncio.Queue` sets per job ID. Worker pushes events; SSE endpoints subscribe and yield `ServerSentEvent` items. Queues are cleaned up on client disconnect.
- **Semaphore-gated concurrency**: At most 5 pipeline runs execute simultaneously, enforced by `asyncio.Semaphore(5)` in `job_worker()`.

## Data & Control Flow

### Startup
1. `uvicorn backend.main:app` loads `main.py`.
2. `lifespan` context manager calls `init_db()` → creates WAL-mode SQLite DB, runs schema, migrates columns, seeds anonymous user.
3. `ensure_base_cv_exists()` copies the default base CV YAML if needed.
4. SPA static files are mounted (if `frontend/dist/` exists).

### Request Path (example: `POST /api/jobs`)
1. FastAPI matches route → `routers/jobs.create_job()`.
2. `get_current_user()` dependency extracts user from JWT (or returns anonymous user in dev mode).
3. A new `jobs` row is inserted with `status='pending'`.
4. `schedule_background_task(job_worker(...))` is called → wraps in `asyncio.create_task()` and registers in `_background_tasks`.
5. The worker task is stored in `_job_tasks[job_id]` for cancellation support.
6. Response returns immediately with job ID and `status='pending'`.

### Worker Pipeline (`job_worker`)
1. Acquire `_semaphore`.
2. Update DB: `pending` → `running`. Push SSE `status` event.
3. Load base CV: DB (`users.base_cv_yaml`) then YAML file fallback via `core.data.load_base_cv()`.
4. Get provider via `core.providers.get_provider(model, user_id=user_id)`.
5. Run AI pipeline via `run_provider_async()` (thread pool) → produces `TailoredCV` + `list[GapItem]`.
6. Render LaTeX via `core.renderer.render_latex()` (sync, fast).
7. Compile PDF via `render_pdf_async()` (thread pool, runs latexmk subprocess).
8. Save `.pdf` and `.tex` to `{data_dir}/output/{user_id}/{company_name}/`.
9. Update DB: `running` → `complete`, storing `tailored_cv_json`, `gap_diff_json`, `pdf_path`.
10. Push SSE `complete` event with full result.
11. On `CancelledError`: set `status='cancelled'` in DB, push SSE, **re-raise**.
12. On other exceptions: set `status='failed'`, push SSE.
13. `finally`: remove from `_job_tasks` registry.

### Settings Flow
- Settings are key-value pairs scoped to `user_id` in the `settings` table.
- On GET, values are merged with `_DEFAULTS`; API keys are masked except last 4 chars.
- On PUT, individual keys are upserted via `INSERT ... ON CONFLICT DO UPDATE`.
- At runtime, `get_setting()` in `settings_cache.py` queries DB directly (no in-memory cache).

### Database Migration
- `init_db()` uses `CREATE TABLE IF NOT EXISTS` for the three core tables.
- Column additions (e.g., `cover_letter_model`, `cv_history_json`) use `ALTER TABLE ADD COLUMN` guarded by `PRAGMA table_info`.
- Clean-slate migration: if the DB file exists but lacks a `users` table (pre-multi-tenant), the file is deleted and recreated.

## Integration Points

| Interface | Direction | Description |
|---|---|---|
| `core/` (domain logic) | Backend → Core | `core.providers` (AI model routing), `core.models` (Pydantic models), `core.renderer` (LaTeX/PDF), `core.data` (CV file I/O), `core.cv_parser`/`core.cv_converter` (CV parsing), `core.cover_letter`/`core.cover_letter_renderer` (cover letter generation/PDF) |
| `frontend/dist/` | Backend → Frontend | Static SPA files served by FastAPI. The catch-all route returns `index.html` for non-API paths. |
| `.env` / environment | System → Backend | `GOOGLE_CLIENT_ID`, `JWT_SECRET`, `CV_MAKER_DB_PATH`, `CORS_ORIGINS`, plus provider API keys (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `GEMINI_WEB_PSID`). Loaded via `python-dotenv`. |
| Google OAuth | Backend → Google | `google.oauth2.id_token.verify_oauth2_token()` validates ID tokens from the frontend sign-in flow. |
| SQLite (`cv_maker.db`) | Internal | All persistent state. WAL mode, `busy_timeout=5000`, foreign keys enabled. |
| latexmk (system) | Backend → OS | Subprocess called via `core.renderer.render_pdf()`. Must be installed on the host. |
| Gemini Web API | Backend → Gemini | For CV PDF parsing (`core.cv_parser`) and optional web-based generation. Uses `gemini_webapi` client library. |

## Operational Notes

- **latexmk required**: The backend calls latexmk as a subprocess for PDF compilation. It must be installed on the host system.
- **WAL mode**: The SQLite WAL mode is set on `init_db()` and persists. Both `init_db()` and `get_db()` re-execute the PRAGMA — it is safe to do so.
- **Thread pool**: AI provider calls and latexmk compilation run in `asyncio.to_thread()`. The default thread pool executor size applies.
- **Dev mode**: Without `GOOGLE_CLIENT_ID`, auth is bypassed. All requests use `ANONYMOUS_USER_ID=1`. The `GOOGLE_CLIENT_ID` env var controls both the Google OAuth audience and the dev/prod auth toggle.
- **Logging**: Standard `logging` module with `basicConfig` at INFO level. Third-party `loguru` from `gemini_webapi` is silenced to suppress noisy internals.
- **CORS**: Configurable via `CORS_ORIGINS` env var (comma-separated). Defaults to `http://localhost:5173` (Vite dev server).
