# CV Maker — Root Repository Atlas

## Project Responsibility

CV Maker is a multi-tenant, AI-powered CV tailoring and cover letter generation platform. A Vue 3 SPA frontend drives the user experience, a FastAPI backend orchestrates job pipelines and persistent state, and a shared `core/` engine owns the domain logic — AI prompt construction, provider abstraction, LaTeX/PDF rendering, and CV parsing. The system supports multiple AI backends (Claude, Gemini, OpenAI), real-time job progress via SSE, Google OAuth authentication, and per-user API key storage.

## System Entry Points

| Entry Point | File | Description |
|---|---|---|
| Docker compose | `docker-compose.yml` | Two-service orchestration: `backend` (FastAPI, port 8000 internal) and `frontend` (Nginx, port 80) |
| HTTP ingress | `nginx.conf` | Reverse proxy: `/api/` → backend, `/assets/` → cached static, `/*` → SPA fallback |
| Backend bootstrap | `backend/main.py` | FastAPI app creation, lifespan (DB init), CORS, router assembly, SPA static serving |
| Frontend bootstrap | `frontend/src/main.ts` | Vue 3 app creation, Pinia + Vue Router install |
| CI/CD | `.github/workflows/deploy.yml` | SSH deploy on push to `master`: `git pull`, `docker compose build/up`, health check |

## Architecture Overview

```
Browser ──▶ Nginx (port 80) ──▶ /api/* ──▶ FastAPI Backend (port 8000)
                    │                          │
                    │                          ├─ backend/routers/   (HTTP handlers)
                    │                          ├─ backend/worker.py  (pipeline executor)
                    │                          ├─ backend/db.py      (SQLite WAL)
                    │                          │
                    │                          ▼
                    │                     core/ (shared engine)
                    │                          ├─ pipeline.py        (AI prompting)
                    │                          ├─ providers/         (AI backends)
                    │                          ├─ renderer.py        (LaTeX → PDF)
                    │                          └─ models.py          (Pydantic models)
                    │
                    └── ▶ SPA static files (Vue 3, built by Vite)
                             ├─ frontend/src/views/    (route pages)
                             ├─ frontend/src/stores/   (Pinia state)
                             └─ frontend/src/components/ (reusable UI)
```

**Three-layer design:**
1. **`frontend/`** — Vue 3 + TypeScript SPA. Composition API, Pinia stores, Vue Router with lazy-loaded views and auth guard.
2. **`backend/`** — FastAPI REST API. JWT auth, CRUD routers, background worker with semaphore (concurrency 5), SSE push, SQLite in WAL mode.
3. **`core/`** — Pure Python engine with zero UI or web dependencies. AI pipeline, provider plugins, LaTeX/PDF rendering, CV parsing/parsing.

**Data layer:** SQLite database at `data/cv_maker.db` (mounted via Docker volume `cv-data`). Base CV stored as `data/base_cv.yaml`. Per-user AI keys stored in DB, server-level keys from `.env`.

## Runtime / Data Flow

### Job Pipeline Lifecycle
```
User submits job form (JobFormView)
  → jobStore.submitJob() → POST /api/jobs → worker.py picks up
  → worker: CREATED → PARSING → TAILORING → RENDERING → COMPLETED
  → SSE events pushed to client (fallback: polling)
  → PDF auto-downloaded on completion
```

### Authentication Flow
```
User clicks Google Sign-In → Google Identity Services → JWT exchange
  → POST /api/auth (ID token) → backend validates, issues JWT
  → Stored in localStorage → attached as Authorization header via apiFetch
  → Anonymous fallback: user_id=1 (ANNONYMOUS_USER_ID)
```

### Tailoring Pipeline
```
BaseCV (YAML/DB) + JobDescription + JobListing
  → core/pipeline.py: build prompt, select provider
  → core/providers/: AI call (Claude/Gemini/OpenAI)
  → JSON extraction with retry logic
  → TailoredCV model
  → Jinja2 LaTeX template (core/templates/cv.tex.jinja)
  → latexmk → PDF
```

## Directory Map

| Directory | Responsibility | Codemap |
|---|---|---|
| `backend/` | FastAPI REST API: auth, routers, background worker, DB, SSE | [backend/codemap.md](backend/codemap.md) |
| `backend/routers/` | HTTP endpoint handlers organized by domain (auth, jobs, CV, cover letter, settings, config) | [backend/routers/codemap.md](backend/routers/codemap.md) |
| `core/` | Shared domain engine: models, AI pipeline, LaTeX/PDF rendering, CV parsing, cover letter generation | [core/codemap.md](core/codemap.md) |
| `core/providers/` | Pluggable AI provider architecture (Claude, Gemini, OpenAI, Gemini Web) | [core/providers/codemap.md](core/providers/codemap.md) |
| `core/templates/` | Jinja2 LaTeX template (`cv.tex.jinja`) — renders `TailoredCV` into professional PDF | [core/templates/codemap.md](core/templates/codemap.md) |
| `data/` | Canonical base CV in YAML (`base_cv.yaml`) — single source of truth for tailoring | [data/codemap.md](data/codemap.md) |
| `frontend/` | Vue 3 + TypeScript SPA root: entry HTML, Vite config, package.json, TypeScript config | [frontend/codemap.md](frontend/codemap.md) |
| `frontend/src/` | Application source: bootstrap (`main.ts`), root shell (`App.vue`), shared types, all feature modules | [frontend/src/codemap.md](frontend/src/codemap.md) |
| `frontend/src/assets/` | Shared CSS styles (pill-group selectors) imported by multiple components | [frontend/src/assets/codemap.md](frontend/src/assets/codemap.md) |
| `frontend/src/components/` | Reusable Vue components: sidebar, session entry, status badge, selectors, PDF drop zone, CV preview, etc. | [frontend/src/components/codemap.md](frontend/src/components/codemap.md) |
| `frontend/src/router/` | Vue Router definitions (6 routes) + `beforeEach` auth guard | [frontend/src/router/codemap.md](frontend/src/router/codemap.md) |
| `frontend/src/stores/` | Pinia state management: `authStore`, `jobStore`, `cvStore` | [frontend/src/stores/codemap.md](frontend/src/stores/codemap.md) |
| `frontend/src/utils/` | Shared utilities: `apiFetch` (authenticated fetch wrapper) | [frontend/src/utils/codemap.md](frontend/src/utils/codemap.md) |
| `frontend/src/views/` | Top-level route-level Vue components: JobForm, JobDetail, BaseCv, CvConverter, Settings, SignIn | [frontend/src/views/codemap.md](frontend/src/views/codemap.md) |

## Root Config / Deployment File Map

| File | Purpose |
|---|---|
| `pyproject.toml` | Python project metadata (`cv-maker` v0.1.0), 16 dependencies, build system (hatchling), Ruff linter, pytest config |
| `docker-compose.yml` | Two-service orchestration: `backend` (FastAPI, expose 8000) + `frontend` (Nginx, port 80:80). Named volume `cv-data` for SQLite + YAML. |
| `docker-compose.prod.yml` | Stub — removed; production uses `docker-compose.yml` directly. |
| `Dockerfile.backend` | Multi-stage: Python 3.12-slim + TeX Live + Node.js (Claude CLI) + uv. Copies `core/` then `backend/`. Runs as `appuser`. |
| `Dockerfile.frontend` | Two-stage: Node build (Vite) → Nginx stable-alpine. Custom `nginx.conf` replaces default. |
| `nginx.conf` | Reverse proxy on port 80: `/api/` → `backend:8000` (300s timeout, SSE unbuffered), `/assets/` → 1y cache immutable, `/*` → SPA fallback. Cloudflare real IP restoration. Security headers. `client_max_body_size 10m`. |
| `.env.example` | Template for required env vars: `GOOGLE_CLIENT_ID`, `JWT_SECRET`, `GEMINI_API_KEY` (server-level for PDF parsing). User-level AI keys set in-app, not here. |
| `.github/workflows/deploy.yml` | GitHub Actions: SSH deploy on push to `master`. Script: `git pull`, `docker compose build`, `docker compose up -d --remove-orphans`, health check (5 retries via curl). |

## Key Integration Points

| Integration | From | To | Mechanism |
|---|---|---|---|
| Frontend ↔ Backend | `frontend/src/utils/apiFetch.ts` | `backend/routers/` | REST over `/api/*`, JWT in `Authorization` header |
| Real-time job updates | `backend/worker.py` | `frontend/src/stores/jobStore.ts` | Server-Sent Events (`GET /api/jobs/{id}/events`), polling fallback |
| AI provider selection | `backend/settings_cache.py` | `core/providers/__init__.py` | Per-user model key → provider factory → API call |
| Base CV persistence | `backend/routers/cv.py` | `core/data.py` → `data/base_cv.yaml` | DB-first with YAML file fallback |
| PDF rendering | `backend/worker.py` | `core/renderer.py` → `core/templates/cv.tex.jinja` | Thread pool via `run_pipeline_async()` |
| Authentication | `frontend/src/stores/authStore.ts` | `backend/auth.py` | Google OAuth ID token → JWT exchange |
| PDF parsing (upload) | `backend/routers/cv.py` | `core/cv_parser.py` | Two-pass Gemini: extract text (PyMuPDF) → structure |
| Cover letter PDF | `backend/routers/cover_letter.py` | `core/cover_letter_renderer.py` | fpdf2 rendering |

## Operational Notes

- **Python version:** ≥3.12 (enforced in `pyproject.toml` and `Dockerfile.backend`)
- **Database:** SQLite in WAL mode. Stored at `/app/data/cv_maker.db` inside container, mapped to Docker volume `cv-data`. Anonymous user ID is hardcoded as `1`.
- **Concurrency:** Background worker semaphore limits concurrent AI jobs to 5.
- **LLM timeouts:** Nginx proxy timeout set to 300s (5 min) to accommodate slow AI responses. SSE buffering disabled for real-time updates.
- **AI keys:** Server-level `GEMINI_API_KEY` in `.env` (for PDF parsing). User-level keys (Anthropic, OpenAI, Gemini, Gemini Web) stored per-user in DB and configured via Settings page.
- **Cloudflare:** Production Nginx config includes Cloudflare real IP restoration. Harmless in local dev — only activates for traffic from Cloudflare CIDRs.
- **Deployment:** Single VPS via GitHub Actions SSH deploy. `docker compose build && up -d` on push to `master`. `.env` is created once on VPS and persists across deploys.
- **Frontend dev:** `npm run dev` with Vite's HMR. API proxy configured in `vite.config.ts`.
- **Backend dev:** `uvicorn backend.main:app --reload`. Requires `core/` package installed (`uv sync`).
- **Linting:** Ruff with rules E (pycodestyle), F (pyflakes), I (isort), S (bandit). Max line length 100.
- **Tests:** pytest with asyncio auto mode, test directory: `tests/`.
