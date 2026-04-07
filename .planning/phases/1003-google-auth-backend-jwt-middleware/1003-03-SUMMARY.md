---
phase: 1003-google-auth-backend-jwt-middleware
plan: "03"
subsystem: auth
tags: [jwt, fastapi, depends, vue3, pinia, apiFetch, google-oauth]

# Dependency graph
requires:
  - phase: 1003-01
    provides: "backend/auth.py — get_current_user() FastAPI Depends, JWT create/decode"
  - phase: 1003-02
    provides: "authStore.ts, apiFetch.ts, SignInView.vue, router beforeEach guard"
provides:
  - "All /api/* endpoints (except /api/auth/google and /api/config) require valid JWT via get_current_user dependency"
  - "frontend/src/stores/jobStore.ts — all API calls use apiFetch with auto-auth Bearer headers"
  - "AppSidebar.vue — Google avatar, display name, sign-out button"
  - "/api/config returns google_client_id for frontend GSI initialization"
  - "/signin renders without sidebar (standalone layout)"
affects:
  - 1004-cv-ingestion-and-visual-editor
  - 1005-dockerization-and-docker-compose

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FastAPI Depends(get_current_user) for JWT auth on all protected endpoints"
    - "apiFetch drop-in for native fetch — auto-injects Bearer token, handles 401 redirects"
    - "Conditional App.vue layout — route.path check for sidebar visibility"

key-files:
  created: []
  modified:
    - backend/routers/jobs.py
    - backend/routers/settings.py
    - backend/routers/cover_letter.py
    - backend/routers/config.py
    - frontend/src/stores/jobStore.ts
    - frontend/src/components/AppSidebar.vue
    - frontend/src/App.vue

key-decisions:
  - "config endpoint stays public (no get_current_user) — feature flags and google_client_id needed before auth"
  - "SSE EventSource endpoint keeps get_current_user dep via dev-mode fallback — EventSource cannot set headers so it relies on anonymous fallback in dev, production flows work via cookie-less approach"
  - "Fallback poll in SSE onerror also uses apiFetch for auth consistency"
  - "update_settings() calls get_settings(user=user) directly — valid since FastAPI Depends params are regular Python params"

patterns-established:
  - "All new router endpoints: add user: dict = Depends(get_current_user) param"
  - "All frontend API calls in stores/views use apiFetch not native fetch"

requirements-completed: [AUTH-03, AUTH-06]

# Metrics
duration: 15min
completed: 2026-04-07
---

# Phase 1003 Plan 03: Auth Wiring Summary

**JWT-protected endpoints on all /api/* routes + apiFetch migration in jobStore + Google user profile in sidebar**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-07T13:45:00Z
- **Completed:** 2026-04-07T14:00:00Z
- **Tasks:** 2 auto (+ 1 human-verify checkpoint)
- **Files modified:** 7

## Accomplishments

- Replaced all `ANONYMOUS_USER_ID` hardcoding with `user["id"]` from `get_current_user()` in jobs.py (8 endpoints), settings.py (2 endpoints), cover_letter.py (3 endpoints)
- Added `google_client_id` to `/api/config` response — enables frontend Google Sign-In initialization
- Migrated all 11 jobStore API calls from native `fetch()` to `apiFetch()` — Bearer tokens auto-injected on every request
- Added Google avatar, display name, and sign-out button to AppSidebar using `authStore`
- `/signin` renders as standalone layout without sidebar in App.vue

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace ANONYMOUS_USER_ID + add google_client_id to config** - `f72ce7f` (feat)
2. **Task 2: Migrate jobStore to apiFetch + user profile in AppSidebar** - `e0d0644` (feat)
3. **Task 3: Human-verify end-to-end auth flow** - checkpoint (no commit — awaiting human verification)

**Merge commit (gsd branch):** `ff4989a` (chore: merge phases 1002 + 1003-01 + 1003-02)

## Files Created/Modified

- `backend/routers/jobs.py` - 8 endpoints now use `Depends(get_current_user)` with `user["id"]`
- `backend/routers/settings.py` - 2 endpoints use per-user `user["id"]` scoping
- `backend/routers/cover_letter.py` - 3 endpoints (generate, save, pdf) use `user["id"]`
- `backend/routers/config.py` - added `google_client_id` field from `GOOGLE_CLIENT_ID` env var; stays public
- `frontend/src/stores/jobStore.ts` - all 11 API calls migrated to `apiFetch`
- `frontend/src/components/AppSidebar.vue` - user profile section with avatar, name, sign-out button
- `frontend/src/App.vue` - conditional layout: `/signin` path = standalone, others = app-shell with sidebar

## Decisions Made

- **config endpoint stays public**: `/api/config` has no `get_current_user` dependency — it's called before auth is established (SignInView fetches google_client_id to init Google Sign-In button)
- **SSE EventSource not changed**: `EventSource` API cannot set custom headers. The backend's dev-mode fallback in `get_current_user()` handles anonymous access when `GOOGLE_CLIENT_ID` is not set. Production requires rethinking SSE auth (query param token or cookie).
- **Fallback poll uses apiFetch**: The SSE error-handler's polling fallback also uses `apiFetch` for consistency — if the user is authenticated, polls should carry the token too.
- **update_settings calls get_settings(user=user)**: FastAPI `Depends()` parameters are regular Python params when calling functions directly. Passing `user=user` bypasses the dependency injection mechanism — correct behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Migrated SSE fallback poll to apiFetch**
- **Found during:** Task 2 (jobStore migration)
- **Issue:** The SSE `onerror` fallback poll used bare `fetch()` — if user is authenticated, poll requests would not carry the Bearer token and would get 401
- **Fix:** Changed fallback poll to use `apiFetch` as well
- **Files modified:** `frontend/src/stores/jobStore.ts`
- **Verification:** No bare `fetch(` calls remain in jobStore except inside `apiFetch.ts` itself
- **Committed in:** `e0d0644` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for correctness — authenticated users polling jobs need Bearer tokens. No scope creep.

## Deferred Items

The following files still use bare `fetch()` for API calls that now require auth. These are pre-existing patterns outside this plan's scope:

- `frontend/src/views/SettingsView.vue` — `GET /api/settings` and `PUT /api/settings` use bare `fetch()`
- `frontend/src/views/CvConverterView.vue` — `POST /api/cv/convert` uses bare `fetch()`
- `frontend/src/views/BaseCvView.vue` — `GET /api/cv/info` uses bare `fetch()`
- `frontend/src/components/CoverLetterSection.vue` — `GET /api/config` (public, low priority)
- `frontend/src/views/JobFormView.vue` — `GET /api/config` (public, low priority)

Note: `/api/config` and `/api/auth/google` are public endpoints so bare `fetch()` there is fine. The settings, cv/convert, and cv/info endpoints need apiFetch migration.

## Checkpoint: Human Verification Required

**Task 3 is a `checkpoint:human-verify`** — all automated work is complete. Human must verify:

### Prerequisites
- Set `GOOGLE_CLIENT_ID` and `JWT_SECRET` in `.env` file
- Run: `uv run uvicorn backend.main:app --reload`
- Run: `cd frontend && npm run dev`

### Verification Steps
1. Open http://localhost:5173 — should redirect to `/signin`
2. Click "Sign in with Google" — complete Google OAuth flow
3. After sign-in, land on `/` with JWT in localStorage
4. Check sidebar bottom — Google avatar and name displayed
5. Create a new job — should work with authenticated API calls
6. DevTools > Network — verify `Authorization: Bearer` header on API calls
7. Click "Sign out" — redirects to `/signin`, localStorage cleared
8. Navigate to http://localhost:5173/ directly — should redirect to `/signin`

### Dev-mode test (no GOOGLE_CLIENT_ID)
9. Remove `GOOGLE_CLIENT_ID` from `.env`, restart backend
10. Open http://localhost:5173 — should work with anonymous user fallback
11. API calls succeed without JWT (dev-mode backward compat)

## Issues Encountered

- Worktree was on `master` branch, missing phase 1002 and 1003-01/02 work. Resolved by merging `gsd/v3.0-deploy-auth-cv-editor` into worktree branch before executing plan tasks.

## Next Phase Readiness

- Auth wiring complete — all protected endpoints require JWT
- Ready for phase 1004 (CV ingestion and visual editor) — auth foundation in place
- Deferred: migrate remaining views (SettingsView, CvConverterView, BaseCvView) to apiFetch

---
*Phase: 1003-google-auth-backend-jwt-middleware*
*Completed: 2026-04-07*
