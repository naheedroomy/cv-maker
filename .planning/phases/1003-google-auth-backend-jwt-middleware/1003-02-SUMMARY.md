---
phase: 1003-google-auth-backend-jwt-middleware
plan: "02"
subsystem: auth
tags: [pinia, vue-router, google-identity-services, jwt, localstorage, typescript]

# Dependency graph
requires:
  - phase: 1003-google-auth-backend-jwt-middleware plan 01
    provides: backend POST /api/auth/google endpoint that exchanges Google ID token for JWT

provides:
  - Pinia auth store (useAuthStore) with JWT/user lifecycle in localStorage
  - apiFetch() drop-in fetch wrapper with Bearer token injection and 401 redirect
  - SignInView.vue with Google Identity Services button, fetches /api/config for client_id
  - Vue Router /signin route with meta.public guard; all other routes protected

affects:
  - 1003-03 (plan 03 wires authStore login into component integration)
  - All existing components that call fetch() — plan 03 will migrate them to apiFetch()

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pinia setup-store pattern (ref/computed/function, return all)
    - Dynamic import of authStore inside router.beforeEach to avoid circular dependency
    - Pre-auth fetch (/api/config) uses plain fetch; post-auth calls use apiFetch
    - Hard redirect via window.location.href for full state reset on 401

key-files:
  created:
    - frontend/src/stores/authStore.ts
    - frontend/src/utils/apiFetch.ts
    - frontend/src/views/SignInView.vue
  modified:
    - frontend/src/router/index.ts
    - frontend/index.html

key-decisions:
  - "Dynamic import of useAuthStore inside beforeEach guard avoids circular dependency between router and store at module load time"
  - "window.location.href for 401 redirect instead of router.push — ensures full page reload and state reset"
  - "Plain fetch for /api/config and /api/auth/google in SignInView — pre-auth calls must not trigger 401 redirect loop"

patterns-established:
  - "apiFetch pattern: auto-Bearer + 401 redirect; use for all authenticated API calls"
  - "Router meta.public guard: only /signin has public: true; all other routes implicitly protected"

requirements-completed: [AUTH-04, AUTH-05]

# Metrics
duration: 2min
completed: 2026-04-07
---

# Phase 1003 Plan 02: Frontend Auth Layer Summary

**Pinia auth store with localStorage JWT persistence, apiFetch Bearer-token wrapper with 401 auto-redirect, and Google Identity Services sign-in page with Vue Router navigation guards**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-07T15:54:49Z
- **Completed:** 2026-04-07T15:56:32Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- `authStore.ts` persists JWT and user in localStorage; exposes `isAuthenticated` computed, `login()`, and `logout()`
- `apiFetch.ts` transparently injects Authorization Bearer header and hard-redirects to /signin on 401
- `SignInView.vue` fetches Google client_id from /api/config, initializes GSI, exchanges credential for JWT via /api/auth/google
- `router/index.ts` has /signin route (public) and beforeEach guard blocking all other routes for unauthenticated users
- TypeScript: zero errors across all five files

## Task Commits

Each task was committed atomically:

1. **Task 1: Create authStore.ts, apiFetch.ts utility, and Google Sign-In page** - `fe5ac42` (feat)
2. **Task 2: Add /signin route and Vue Router auth guards** - `61adfd2` (feat)

## Files Created/Modified
- `frontend/src/stores/authStore.ts` - Pinia setup-store; jwt/user refs, isAuthenticated computed, login/logout with localStorage sync
- `frontend/src/utils/apiFetch.ts` - Fetch wrapper; adds Bearer token, handles 401 with window.location redirect
- `frontend/src/views/SignInView.vue` - Google Sign-In page; fetches /api/config for client_id, renders GSI button, calls authStore.login on success
- `frontend/src/router/index.ts` - Added /signin route with meta.public, beforeEach guard with dynamic authStore import
- `frontend/index.html` - Added Google Identity Services script tag in head

## Decisions Made
- Dynamic import of `useAuthStore` inside `router.beforeEach` avoids circular dependency (router imports at module level would run before Pinia is initialized)
- `window.location.href = '/signin'` instead of `router.push()` on 401 — ensures full page state reset on session expiry
- `/api/config` and `/api/auth/google` use plain `fetch` in SignInView (pre-auth context) — using apiFetch would cause a redirect loop since no JWT exists yet

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required at this step. Google Client ID is loaded dynamically from /api/config (configured in Plan 03).

## Known Stubs

None. The SignInView fetches `google_client_id` from `/api/config` — this field is added by Plan 03. Until Plan 03 is complete, the sign-in page will show "Google Sign-In is not configured." This is intentional gating, not a stub.

## Next Phase Readiness

- Auth layer complete: store, HTTP wrapper, sign-in page, and router guards are all ready
- Plan 03 wires `authStore.login` into existing app components and adds `google_client_id` to `/api/config`
- Plan 03 should also migrate existing `fetch()` calls in jobStore and other stores to `apiFetch()`

---
*Phase: 1003-google-auth-backend-jwt-middleware*
*Completed: 2026-04-07*
