---
phase: 1003-google-auth-backend-jwt-middleware
plan: "01"
subsystem: auth
tags: [jwt, google-oauth, pyjwt, google-auth, fastapi, cors]

# Dependency graph
requires:
  - phase: 1002-multi-tenant-data-model
    provides: users table schema, ANONYMOUS_USER_ID, get_db() pattern
provides:
  - backend/auth.py with verify_google_token, create_jwt, decode_jwt, get_current_user
  - POST /api/auth/google endpoint that exchanges Google ID tokens for JWTs
  - Dev-mode fallback returning ANONYMOUS_USER_ID when GOOGLE_CLIENT_ID not set
  - CORS updated with CORS_ORIGINS env var and allow_credentials=True
affects: [1003-02, 1003-03, all protected endpoints using get_current_user]

# Tech tracking
tech-stack:
  added:
    - PyJWT>=2.9.0 (HS256 JWT issuance and decoding)
    - google-auth>=2.40.0 (Google ID token verification)
    - pytest-asyncio>=0.23.0 (async test support, asyncio_mode=auto)
  patterns:
    - FastAPI Depends() for auth injection via get_current_user
    - Dev-mode fallback pattern: missing GOOGLE_CLIENT_ID returns ANONYMOUS_USER_ID
    - User upsert ON CONFLICT pattern for idempotent sign-in

key-files:
  created:
    - backend/auth.py
    - backend/routers/auth.py
    - tests/test_auth.py
  modified:
    - backend/main.py
    - pyproject.toml
    - .env.example
    - uv.lock

key-decisions:
  - "PyJWT over python-jose: PyJWT is the standard, actively maintained JWT library for Python; no need for both libraries"
  - "asyncio_mode=auto in pytest config: removes need for @pytest.mark.asyncio decorator on every async test"
  - "google-auth for token verification: official Google library, handles key fetching and expiry automatically"
  - "CORS_ORIGINS env var with comma-split: supports multiple origins for staging+production without code changes"

patterns-established:
  - "get_current_user: FastAPI dependency injected via Header; returns user dict with id, email, name, picture"
  - "Dev-mode fallback: GOOGLE_CLIENT_ID absent => ANONYMOUS_USER_ID user, present => 401 on missing token"
  - "JWT payload: user_id, email, name, picture, exp (7-day) via HS256 with JWT_SECRET env var"

requirements-completed: [AUTH-01, AUTH-02]

# Metrics
duration: 4min
completed: 2026-04-07
---

# Phase 1003 Plan 01: Google Auth Backend JWT Middleware Summary

**HS256 JWT auth core with Google ID token verification, dev-mode fallback, and POST /api/auth/google endpoint registered in FastAPI**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-07T15:60:07Z
- **Completed:** 2026-04-07T16:04:07Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created `backend/auth.py` with all 4 auth functions: `verify_google_token`, `create_jwt`, `decode_jwt`, `get_current_user`
- Created `backend/routers/auth.py` with POST /api/auth/google — verifies Google token, upserts user, returns JWT + user dict
- Registered auth router as first route in main.py; updated CORS with `CORS_ORIGINS` env var and `allow_credentials=True`
- Added `PyJWT>=2.9.0`, `google-auth>=2.40.0`, `pytest-asyncio>=0.23.0` to pyproject.toml; all 6 auth unit tests pass

## Task Commits

Each task was committed atomically:

1. **RED: Failing tests** - `0d2b8e3` (test: add 6 failing auth tests, add dependencies)
2. **Task 1: backend/auth.py + .env.example** - `34ae480` (feat: JWT and Google token verification module)
3. **Task 2: backend/routers/auth.py + main.py** - `0595062` (feat: POST /api/auth/google + router registration)
4. **uv.lock update** - `bd8dae5` (chore: update lockfile with new dependencies)

## Files Created/Modified
- `backend/auth.py` - verify_google_token, create_jwt, decode_jwt, get_current_user FastAPI dependency
- `backend/routers/auth.py` - POST /api/auth/google with user upsert and JWT issuance
- `tests/test_auth.py` - 6 unit tests covering JWT roundtrip, expiry, wrong secret, dev-mode fallback, production 401
- `backend/main.py` - auth router registered, CORS updated with env-configurable origins and credentials
- `pyproject.toml` - PyJWT, google-auth added to deps; pytest-asyncio added to dev; asyncio_mode=auto
- `.env.example` - GOOGLE_CLIENT_ID and JWT_SECRET documented
- `uv.lock` - lockfile updated with new packages

## Decisions Made
- `asyncio_mode = "auto"` in pytest config: removes need for `@pytest.mark.asyncio` on every async test — cleaner test files
- `pytest-asyncio` over anyio for async test support: more familiar pattern, cleaner decorator syntax
- `google-auth` for token verification: official Google library, handles JWKS key fetching and caching automatically

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added pytest-asyncio as dev dependency**
- **Found during:** Task 1 RED phase
- **Issue:** Plan uses async test functions (`get_current_user` is async) but pytest-asyncio was not in dev dependencies
- **Fix:** Added `pytest-asyncio>=0.23.0` to `[dependency-groups] dev` and `asyncio_mode = "auto"` to `[tool.pytest.ini_options]`
- **Files modified:** pyproject.toml
- **Verification:** All 6 async tests pass
- **Committed in:** 0d2b8e3 (RED phase commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical — missing test infrastructure dependency)
**Impact on plan:** Required for async test execution. No scope creep.

## Issues Encountered
None - implementation was straightforward.

## Known Stubs
None - all functions are fully implemented. `verify_google_token` requires a real `GOOGLE_CLIENT_ID` env var at runtime (Google validates the token against the registered client ID), which is expected per the plan's `user_setup` requirements.

## User Setup Required
Google Cloud and JWT configuration required before auth endpoints work in production. Users must:
1. Create OAuth 2.0 Client ID in Google Cloud Console (Web application type)
2. Add `http://localhost:5173` as authorized JavaScript origin
3. Set `GOOGLE_CLIENT_ID=<client-id>.apps.googleusercontent.com` in `.env`
4. Set `JWT_SECRET=<64-char-random>` in `.env` (generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"`)

## Next Phase Readiness
- Auth core complete — `get_current_user` dependency ready to inject into any protected endpoint
- Dev-mode works without Google credentials (ANONYMOUS_USER_ID fallback)
- Ready for Phase 1003-02 (frontend Google Sign-In integration)
- Ready for Phase 1003-03 (wire get_current_user into jobs/settings/config routers)

---
*Phase: 1003-google-auth-backend-jwt-middleware*
*Completed: 2026-04-07*
