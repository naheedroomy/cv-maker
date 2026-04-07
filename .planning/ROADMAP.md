# Roadmap: CV Maker

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-04-04) — [archive](milestones/)
- ✅ **v2.0 Full-Stack Rebuild** — Phases 5-9 (shipped 2026-04-05) — [archive](milestones/v2.0-ROADMAP.md)
- 🚧 **v3.0 Deploy, Auth & CV Editor** — Phases 1002-1006 (in progress) — branch: `feature/deployment`

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-04-04</summary>

- [x] Phase 1: Data Foundation (1/1 plans) — completed 2026-04-03
- [x] Phase 2: LaTeX Renderer (2/2 plans) — completed 2026-04-04
- [x] Phase 3: AI Pipeline (3/3 plans) — completed 2026-04-04
- [x] Phase 4: Streamlit UI (2/2 plans) — completed 2026-04-04

</details>

<details>
<summary>✅ v2.0 Full-Stack Rebuild (Phases 5-9) — SHIPPED 2026-04-05</summary>

- [x] Phase 5: Backend Foundation (2/2 plans) — completed 2026-04-04
- [x] Phase 6: Job Queue & API (3/3 plans) — completed 2026-04-04
- [x] Phase 7: Vue Frontend (3/3 plans) — completed 2026-04-04
- [x] Phase 8: Production Wiring (2/2 plans) — completed 2026-04-04
- [x] Phase 9: Gemini Provider (4/4 plans) — completed 2026-04-05

</details>

<details>
<summary>🚧 v3.0 Deploy, Auth & CV Editor (Phases 1002-1006) — IN PROGRESS</summary>

- [x] Phase 1002: Multi-Tenant DB Schema (3/3 plans)
- [ ] Phase 1003: Google Auth Backend + JWT Middleware (0/3 plans)
- [ ] Phase 1004: CV Ingestion & Visual Editor (0/3 plans)
- [ ] Phase 1005: Dockerization & docker-compose (0/0 plans)
- [ ] Phase 1006: CI/CD, Domain & HTTPS (0/0 plans)

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 1/1 | Complete | 2026-04-03 |
| 2. LaTeX Renderer | v1.0 | 2/2 | Complete | 2026-04-04 |
| 3. AI Pipeline | v1.0 | 3/3 | Complete | 2026-04-04 |
| 4. Streamlit UI | v1.0 | 2/2 | Complete | 2026-04-04 |
| 5. Backend Foundation | v2.0 | 2/2 | Complete | 2026-04-04 |
| 6. Job Queue & API | v2.0 | 3/3 | Complete | 2026-04-04 |
| 7. Vue Frontend | v2.0 | 3/3 | Complete | 2026-04-04 |
| 8. Production Wiring | v2.0 | 2/2 | Complete | 2026-04-04 |
| 9. Gemini Provider | v2.0 | 4/4 | Complete | 2026-04-05 |
| 1002. Multi-Tenant DB Schema | v3.0 | 3/3 | Complete    | 2026-04-07 |
| 1003. Google Auth Backend + JWT Middleware | v3.0 | 2/3 | Complete    | 2026-04-07 |
| 1004. CV Ingestion & Visual Editor | v3.0 | 3/3 | Complete    | 2026-04-07 |
| 1005. Dockerization & docker-compose | v3.0 | 2/2 | Complete    | 2026-04-07 |
| 1006. CI/CD, Domain & HTTPS | v3.0 | 2/2 | Complete    | 2026-04-07 |

---

## v3.0 Milestone: Deploy, Auth & CV Editor

**Branch:** `feature/deployment`
**Goal:** Ship CV Maker as a public multi-user web service — Docker deployment via GitHub Actions, Google Sign-In, per-user data isolation, and a visual CV editor with AI-assisted parsing from uploaded CVs.
**Requirements covered:** TENANT-01–05, AUTH-01–06, CVED-01–06, DEPLOY-01–06 (23 total)

---

### Phase 1002: Multi-Tenant DB Schema

**Goal:** Migrate the SQLite database to a multi-tenant model — add a `users` table and attach `user_id` foreign keys to all user-owned tables (jobs, settings, api_keys, base CV). This is a prerequisite for all auth and per-user features.

**Branch:** `gsd/phase-1002-multi-tenant-db`

**Requirements:**
- TENANT-01: Users table created automatically on first sign-in (google_id, email, name, created_at)
- TENANT-02: All CV tailoring jobs scoped to authenticated user (user_id FK on jobs table)
- TENANT-03: Settings (model preferences, base URL) stored and loaded per user
- TENANT-04: API keys (Anthropic, Gemini, OpenAI) stored and resolved per user
- TENANT-05: Users can only view and interact with their own data — no cross-user data leakage

**Success Criteria:**
1. The `users` table exists after server startup with columns: `id`, `google_id`, `email`, `name`, `created_at`
2. The `jobs` table has a non-null `user_id` FK column referencing `users.id`; existing rows have a NULL sentinel or default user row
3. The `settings` table has a `user_id` FK — querying settings for user A does not return user B's preferences
4. The `api_keys` table has a `user_id` FK — key resolution is scoped per user at the DB query level
5. A query for one user's jobs returns zero results when executed with a different user's `user_id` (no cross-user leakage)

**Plans:**
3/3 plans complete
- [x] 1002-01-PLAN.md — DB schema rewrite: users table, multi-tenant migration, seed anonymous user
- [x] 1002-02-PLAN.md — Settings cache rewrite: eliminate cache, async get_setting/get_api_key with user_id
- [x] 1002-03-PLAN.md — Router & worker wiring: thread user_id through all DB queries, provider refactor

---

### Phase 1003: Google Auth Backend + JWT Middleware

**Goal:** Add Google OAuth 2.0 sign-in to the backend — verify Google ID tokens, upsert users into the DB, issue signed JWTs, and protect all `/api/*` endpoints with JWT middleware. Add a sign-in page and Vue Router auth guards to the frontend.

**Branch:** `gsd/phase-1003-google-auth`

**Requirements:**
- AUTH-01: User can sign in using their Google account (Google OAuth 2.0 via ID token)
- AUTH-02: Backend verifies Google ID token and issues a signed JWT stored in localStorage
- AUTH-03: All `/api/*` endpoints require a valid JWT (middleware returns 401 if missing/invalid)
- AUTH-04: Frontend Vue Router guards redirect unauthenticated users to the sign-in page
- AUTH-05: User can sign out, which clears the JWT from localStorage
- AUTH-06: User's name and profile picture from Google are displayed in the app header/sidebar

**Success Criteria:**
1. Clicking "Sign in with Google" completes the OAuth flow and stores a JWT in `localStorage` — the user lands on the app dashboard
2. Calling any `/api/*` endpoint without a JWT (or with an expired one) returns HTTP 401 — no data is returned
3. Navigating to `/` while unauthenticated redirects to `/signin` — the Vue Router guard fires before any data fetch
4. Clicking "Sign out" removes the JWT from `localStorage` and redirects to `/signin` — the next page load requires re-authentication
5. The app header/sidebar displays the signed-in user's Google display name and profile picture after login

**Plans:** 3/3 plans complete
- [x] 1003-01-PLAN.md — Backend auth core: Google token verification, JWT issuance/decoding, get_current_user dependency, auth router
- [x] 1003-02-PLAN.md — Frontend auth: authStore, apiFetch utility, SignInView, Vue Router guards
- [ ] 1003-03-PLAN.md — Integration wiring: replace ANONYMOUS_USER_ID in all routers, migrate jobStore to apiFetch, user profile in sidebar

---

### Phase 1004: CV Ingestion & Visual Editor

**Goal:** Let users upload a PDF of their existing CV, have AI parse it into the structured BaseCV model via a two-pass Gemini pipeline (OCR + structuring), then view and edit their parsed CV in a sectioned visual editor. The saved CV persists per user and is used as the base for all tailoring jobs.

**Branch:** `gsd/phase-1004-cv-editor`

**Requirements:**
- CVED-01: User can upload a PDF file containing their existing CV
- CVED-02: AI parses the uploaded CV and extracts structured data matching the BaseCV model (experience, skills, education, summary, contact)
- CVED-03: User sees a visual sectioned editor with their parsed CV (Work Experience, Education, Skills, Summary, Contact)
- CVED-04: User can add, edit, and delete individual entries within each CV section
- CVED-05: User can save their CV and it persists in the DB under their account
- CVED-06: The saved CV is used as the base CV when tailoring new job applications

**Success Criteria:**
1. Uploading a PDF file triggers AI parsing and the parsed CV populates the visual editor within a few seconds — no raw YAML is shown to the user
2. Each CV section (Work Experience, Education, Skills, Summary, Contact) is rendered as an independently editable panel — fields match the `BaseCV` Pydantic model
3. The user can add a new work experience entry, fill in the fields, and see it appear in the editor list; the same is true for Education and Skills
4. The user can delete an existing entry from any section — the entry is removed from the editor and the change is reflected on save
5. Clicking "Save CV" persists the current editor state to the DB under the authenticated user's `user_id` — a page reload restores the exact same CV
6. Submitting a new tailoring job uses the DB-stored CV (not a static YAML file) as the base CV input to the AI pipeline

**Plans:** 3/3 plans complete
- [x] 1004-01-PLAN.md — Backend: PDF parser (pymupdf + Gemini two-pass), CV CRUD API (upload, get, put, delete), integration tests
- [x] 1004-02-PLAN.md — Frontend: BaseCV types, cvStore, PdfDropZone, visual sectioned CV editor (replace BaseCvView)
- [x] 1004-03-PLAN.md — Pipeline integration: worker loads CV from DB, sidebar CV status, end-to-end verification

---

### Phase 1005: Dockerization & docker-compose

**Goal:** Containerize the entire application — backend (Python + LaTeX), frontend (Vue SPA served by Nginx), and wire them together with docker-compose and an Nginx reverse proxy that routes `/api/*` to the backend and `/` to the frontend static build.

**Branch:** `gsd/phase-1005-docker`

**Requirements:**
- DEPLOY-01: App runs as Docker containers (backend + frontend) orchestrated by docker-compose
- DEPLOY-02: Backend Docker image includes Python runtime, LaTeX (texlive), and all Python dependencies
- DEPLOY-03: Frontend Docker image builds Vue SPA and serves it via Nginx
- DEPLOY-05: Nginx routes `/api/*` requests to backend container and `/` to frontend SPA

**Success Criteria:**
1. `docker-compose up --build` from the repo root starts all containers without errors — the app is reachable at `http://localhost`
2. The backend container serves the FastAPI app and can compile a PDF using `latexmk` — a tailoring job runs end-to-end inside the container
3. The frontend container serves the compiled Vue SPA static files — the app loads correctly at `http://localhost/`
4. Nginx correctly proxies `http://localhost/api/health` to the backend and returns a 200 response; `http://localhost/` returns the Vue SPA `index.html`
5. `docker-compose down && docker-compose up` (no `--build`) starts the app from cached images without re-installing dependencies

**Plans:**
2/2 plans complete

---

### Phase 1006: CI/CD, Domain & HTTPS

**Goal:** Automate build and deployment via GitHub Actions — on push to `main`, build Docker images, push to a registry, SSH into the VPS and pull + restart containers. Configure the domain and HTTPS so the app is publicly accessible at a named URL with TLS.

**Branch:** `gsd/phase-1006-cicd-domain`

**Requirements:**
- DEPLOY-04: GitHub Actions workflow builds images and deploys to VPS via SSH on push to main
- DEPLOY-06: App is accessible via `resume.xenohass.work` (HTTPS handled by Cloudflare Flexible SSL)

**Success Criteria:**
1. Pushing a commit to `main` triggers the GitHub Actions workflow — the Actions run log shows build, push, and SSH deploy steps completing successfully
2. After a successful deploy, the new version is running on the VPS — a changed string in the UI is visible at the public domain without manual intervention
3. The app is reachable at `https://resume.xenohass.work` with a valid TLS certificate — the browser shows a secure padlock, not a certificate warning
4. HTTP requests to `http://resume.xenohass.work` are automatically redirected to `https://resume.xenohass.work` — no plain-text access is possible (Cloudflare "Always Use HTTPS")
5. GitHub Actions secrets (`VPS_HOST`, `VPS_USER`, `SSH_PRIVATE_KEY`) are the only credentials required — GHCR auth uses the automatic `GITHUB_TOKEN`, no hardcoded secrets in the repository

**Plans:**
2/2 plans complete
- [x] 1006-02-PLAN.md — Production Nginx config (Cloudflare), VPS deployment documentation

---

## Backlog

### Phase 999.1: Visual template selector in Settings (BACKLOG)

**Goal:** Let users choose from multiple LaTeX CV templates via a visual gallery in the Settings panel. Each template shows a thumbnail preview; the selected template is used for all PDF renders.
**Scope:** Multiple .tex.jinja templates, template metadata (name, preview image), settings DB field, renderer template selection, frontend preview gallery component.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 1000: Cover Letter Generator

**Goal:** Users can generate a tailored cover letter alongside their tailored CV — using the base CV, job listing, and tailored CV output as inputs. Cover letters sound human (no AI-smell) via humanizer-inspired anti-pattern rules and a two-pass generate-then-self-critique architecture.
**Scope:**
- User notes field: free-text bullet points the user wants woven into the cover letter (e.g., "mention I'm relocating to Berlin", "highlight my K8s migration project")
- New cover letter prompt with anti-AI-smell rules (no significance inflation, no promotional language, simple verbs, varied rhythm, specificity over scope, no generic conclusions)
- Two-pass architecture: generate draft → self-critique for AI tells → revise
- Reuse existing provider abstraction (all 4 providers)
- New Pydantic model for cover letter output
- New API endpoint (POST /api/jobs/:id/cover-letter or integrated into job pipeline)
- Vue component for cover letter preview + download with editable notes input
- Optional: PDF rendering via LaTeX or plain text output
- Creativity slider applies to cover letter tone/boldness
**Branch:** `feature/cover-letter` (not master direct)
**Requirements**: CL-CORE, CL-PROMPT, CL-PDF, CL-DB, CL-TONE, CL-UI, CL-NOTES, CL-EDIT, CL-API, CL-WIRE, CL-BRANCH
**Depends on:** Current codebase (no phase dependency)
**Plans:** 3/3 plans complete

Plans:
- [x] 1000-01-PLAN.md — Backend core: cover letter generation module, fpdf2 renderer, DB migration, API schemas
- [x] 1000-02-PLAN.md — Frontend: ToneSelector, CoverLetterSection components, types, store actions
- [x] 1000-03-PLAN.md — Integration: API router, main.py wiring, JobDetailView integration, end-to-end verification

### Phase 1001: Frontend UX Revamp & Project Restructure

**Goal:** Revamp the frontend UX for a cleaner, less clunky experience — 3-tab layout for job detail, unified pill selectors, 3-level button hierarchy, sidebar facelift. Restructure the repo folder layout to flatten src/cv_maker/ into core/ and delete stray files.
**Scope:**
- Frontend UX cleanup: 3-tab job detail layout (CV / Cover Letter / Analysis), button hierarchy, selector unification
- Cover letter section promoted to its own tab for discoverability
- Regenerate panel button style corrections (Secondary toggle, Primary confirm)
- Sidebar facelift: active left-border indicator, proper session entry spacing
- Project folder restructure: rename src/cv_maker/ to core/, update all imports, delete stray files
**Requirements**: REPO-RENAME, REPO-CLEANUP, UX-SELECTORS, UX-BUTTONS, UX-SIDEBAR, UX-TABS
**Depends on:** Phase 1000
**Plans:** 3/3 plans complete

Plans:
- [x] 1001-01-PLAN.md — Repo restructure: rename src/cv_maker/ to core/, update imports, delete stray files
- [x] 1001-02-PLAN.md — Shared selector CSS, button hierarchy fixes, sidebar redesign
- [x] 1001-03-PLAN.md — 3-tab layout in JobDetailView, CoverLetterSection tab adaptation, visual checkpoint
