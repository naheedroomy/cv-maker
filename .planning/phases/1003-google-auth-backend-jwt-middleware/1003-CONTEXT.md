# Phase 1003: Google Auth Backend + JWT Middleware - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Google OAuth 2.0 sign-in to the backend and frontend. Deliver:
1. Backend: Google ID token verification, JWT issuance, `get_current_user()` dependency
2. Backend: Auth router (`POST /api/auth/google`), JWT middleware on all `/api/*` endpoints
3. Frontend: Sign-in page (`/signin`), Vue Router auth guards, `authStore`, `apiFetch()` wrapper
4. Frontend: User profile display in sidebar (avatar, name, sign-out)
5. Replace all `ANONYMOUS_USER_ID` usages with real JWT user ID from `get_current_user()`

This phase does **not** include: CV upload/parse (Phase 1004), Docker (Phase 1005), or domain/HTTPS (Phase 1006).

</domain>

<decisions>
## Implementation Decisions

### D-01: Auth Flow Architecture
- Frontend-initiated ID token flow using Google Identity Services (GSI) — `google.accounts.id.initialize()` in browser sends ID token to `POST /api/auth/google`
- Backend verifies ID token using `google-auth-library[pyopenid]` (`google.oauth2.id_token.verify_oauth2_token()`)
- JWT signed with PyJWT using HS256, `JWT_SECRET` env var, 7-day expiry. Claims: `user_id`, `email`, `name`, `picture`, `exp`
- JWT stored in `localStorage` on frontend (per AUTH-02 requirement)

### D-02: Backend Auth Structure
- New `backend/auth.py` module — contains `verify_google_token()`, `create_jwt()`, `decode_jwt()`, `get_current_user()` FastAPI dependency
- New `backend/routers/auth.py` — `POST /api/auth/google` accepts `{id_token}`, verifies, upserts user, returns `{jwt, user}`
- JWT middleware via `FastAPI Depends(get_current_user)` applied per-router (not global middleware)
- `get_current_user()` extracts JWT from `Authorization: Bearer <token>` header, decodes, returns user dict with `id` field
- Dev-mode fallback: if no JWT provided, `get_current_user()` returns `ANONYMOUS_USER_ID` user — backward compat until Google Client ID is configured

### D-03: Frontend Auth UX
- Dedicated `/signin` route — centered card with Google Sign-In button (GSI rendered), app logo/name above. No email/password fields.
- User profile in AppSidebar.vue bottom section — avatar (Google picture URL), display name, sign-out button
- New `authStore.ts` in Pinia — stores `jwt`, `user` (name, email, picture), `isAuthenticated` computed. `login()` and `logout()` actions.
- `apiFetch()` utility wraps native `fetch()` — auto-adds `Authorization: Bearer` header from authStore. All existing API calls updated to use it.

### D-04: API Security Model
- Public endpoints (no auth required): `POST /api/auth/google` and `GET /api/config`
- CORS via `CORS_ORIGINS` env var (default `http://localhost:5173` for Vite dev). Applied via FastAPI `CORSMiddleware`.
- `GOOGLE_CLIENT_ID` env var — used by both frontend (via `/api/config` response) and backend (token verification)
- User upsert on sign-in: `INSERT OR REPLACE` by `google_id` — creates user on first sign-in, updates email/name on subsequent sign-ins. Returns user row with `id` for JWT claims.

### Claude's Discretion
- Exact Google Identity Services script loading approach (inline `<script>` vs dynamic load)
- Whether to add refresh token rotation or keep simple 7-day JWT expiry
- Sign-in page visual styling details (colors, spacing)
- Whether `apiFetch()` should auto-redirect to `/signin` on 401 response
- Index creation on `users.google_id` (already UNIQUE, may not need separate index)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Auth Dependencies (Phase 1002)
- `backend/db.py` — `ANONYMOUS_USER_ID` constant, `users` table schema, `get_db()`, `init_db()`
- `backend/settings_cache.py` — `get_api_key()`, `get_setting()` now async with `user_id` param

### Routers to Wire Auth Into
- `backend/routers/jobs.py` — Replace `ANONYMOUS_USER_ID` with `user["id"]` from `get_current_user()`
- `backend/routers/settings.py` — Replace `ANONYMOUS_USER_ID` with `user["id"]`
- `backend/routers/cover_letter.py` — Replace `ANONYMOUS_USER_ID` with `user["id"]`
- `backend/routers/config.py` — Add `google_client_id` to config response; this endpoint stays public

### Frontend Structure
- `frontend/src/router/index.ts` — Add `/signin` route and navigation guards
- `frontend/src/components/AppSidebar.vue` — Add user profile section
- `frontend/src/stores/jobStore.ts` — Update API calls to use `apiFetch()`
- `frontend/src/App.vue` — App shell structure

### Requirements
- `.planning/REQUIREMENTS.md` AUTH-01 through AUTH-06

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/db.py` `get_db()` — async SQLite connection with FK enforcement; reuse for user upsert queries
- `backend/db.py` `ANONYMOUS_USER_ID = 1` — grep target for replacement with `user["id"]`
- `frontend/src/stores/jobStore.ts` — Pinia setup-store pattern with `storeToRefs`; replicate for `authStore`
- `frontend/src/components/ModelSelector.vue` — pill-selector component pattern; reusable for any UI elements on sign-in page

### Established Patterns
- FastAPI routers use `get_db()` dependency injection — extend with `get_current_user()` dependency
- Frontend uses native `fetch()` for all API calls (no Axios per CLAUDE.md constraint)
- Vue Router uses `createWebHistory()` — add `beforeEach` guard for auth check
- Pinia stores export setup functions with `storeToRefs` pattern

### Integration Points
- `backend/main.py` — Register auth router, add CORS middleware
- `backend/worker.py` — Background worker does NOT need auth (internal, already has job_id)
- `core/providers/__init__.py` — `get_provider()` already async; will need user_id passed through for per-user API keys

</code_context>

<specifics>
## Specific Ideas

- The `ANONYMOUS_USER_ID` constant is a deliberate grep target (per Phase 1002 D-09) — every usage becomes `user["id"]` from the JWT dependency
- Worker.py does NOT need auth middleware — it operates on jobs already created by authenticated users
- `apiFetch()` should handle 401 responses by clearing the JWT and redirecting to `/signin`
- CORS must allow credentials for the Authorization header to work cross-origin in dev

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 1003-google-auth-backend-jwt-middleware*
*Context gathered: 2026-04-07 via smart discuss*
