# AGENTS.md

## Start Here

- Read `codemap.md` first; it is the verified repository atlas. Follow local `codemap.md` files in `backend/`, `core/`, `frontend/`, and subdirectories when changing that area.
- Trust executable config over prose when they disagree. Known examples: deploy runs from `master` (not `main`), production uses `docker-compose.yml` (the prod compose file is removed/stubbed), and deployment uses `VPS_PASSWORD` in GitHub Actions.

## Commands Agents Commonly Guess Wrong

- Python deps: `uv sync` (project uses `uv` + hatchling; do not switch to pip/setup.py workflows).
- Backend dev: `uv run uvicorn backend.main:app --reload --port 8000`.
- Frontend dev: `cd frontend && npm run dev` (Vite on 5173; `/api` proxies to `localhost:8000` without path rewrite).
- Docker dev/prod shape: `docker compose up --build` serves frontend on port 80 and backend only inside compose on 8000.
- Python tests: `uv run pytest` (`tests/`, `pytest-asyncio` auto mode).
- Python lint: `uv run ruff check .` (line length 100; rules `E,F,I,S`; `assert` allowed under `tests/**`).
- Frontend verification: `cd frontend && npm run build` runs `vue-tsc --build` before `vite build`; there are no frontend test scripts/configs.

## Architecture Boundaries

- `frontend/`: Vue 3 + TypeScript SPA. Entry `frontend/src/main.ts`; router/auth guard in `frontend/src/router/index.ts`; Pinia stores in `frontend/src/stores/`.
- `backend/`: FastAPI API. Entry `backend/main.py`; API prefix is `/api`; startup runs `init_db()` and `ensure_base_cv_exists()`; serves `frontend/dist` only when present.
- `core/`: pure Python domain engine with no web/UI dependency. Owns Pydantic models, provider abstraction, prompt/pipeline logic, parsing, and LaTeX/PDF rendering.
- `backend/pipeline_runner.py` is the async boundary for sync core pipeline/rendering; keep long AI/render work off the event loop with the existing `asyncio.to_thread()` pattern.
- `backend/worker.py` owns job lifecycle and SSE: pending → running → complete/failed/cancelled, with `asyncio.Semaphore(5)`. If handling cancellation, update DB then re-raise `CancelledError`.

## Data, Auth, and Env Gotchas

- SQLite path comes from `CV_MAKER_DB_PATH` (default `backend/cv_maker.db`; Docker sets `/app/data/cv_maker.db`). Connections enable WAL, `busy_timeout=5000`, and foreign keys.
- DB writes should use `BEGIN IMMEDIATE`; do not hold/reuse a DB connection across a long pipeline run.
- Anonymous/local user id is hardcoded as `1`; per-user base CV overrides live in `users.base_cv_yaml`, falling back to `data/base_cv.yaml`.
- `.env` server-level `GEMINI_API_KEY` is for PDF parsing/OCR only. Tailoring provider keys are per-user settings stored in the DB, not `.env`.
- Claude CLI provider (`claude-haiku`) needs a host `claude` binary and is not reliable in Docker; Docker users should configure Claude API, Gemini, Gemini Web, or OpenAI in Settings.
- `nginx.conf` proxies `/api/` to backend with 300s timeout and SSE buffering disabled; keep long-running routes compatible with that setup.

## Rendering and Provider Quirks

- LaTeX templates use custom Jinja delimiters (`\BLOCK{`, `\VAR{`, `\#{`) and `autoescape=False`; standard Jinja delimiters can collide with LaTeX braces.
- `core/providers/__init__.py` uses lazy provider imports and resolves model/user keys through the DB-backed settings path; avoid module-scope provider imports that force optional SDKs early.
- Gemini Web uses a per-user `__Secure-1PSID` cookie setting; loguru noise from `gemini_webapi` is intentionally disabled in `backend/main.py`.

## Deployment Notes

- GitHub Actions deploys only on push to `master`, SSHes to `/opt/cv-maker/cv-maker`, resets to `origin/master`, then runs `docker compose build` and `docker compose up -d --remove-orphans`.
- The VPS `.env` persists outside deploys. Do not bake secrets into images or repository files.
