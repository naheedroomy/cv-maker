---
phase: 1003-google-auth-backend-jwt-middleware
verified: 2026-04-07T18:00:00Z
status: human_needed
score: 12/12 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 11/12
  gaps_closed:
    - "backend/routers/cv_convert.py now has Depends(get_current_user) on both GET /api/cv/info and POST /api/cv/convert (commit 279ed9b)"
    - "SettingsView.vue migrated from bare fetch() to apiFetch() for GET /api/settings and PUT /api/settings (commit 279ed9b)"
    - "CvConverterView.vue migrated from bare fetch() to apiFetch() for POST /api/cv/convert and GET /api/config (commit 279ed9b)"
    - "BaseCvView.vue migrated from bare fetch() to apiFetch() for GET /api/cv/info (commit 279ed9b)"
    - "CoverLetterSection.vue and RegeneratePanel.vue also migrated to apiFetch() (commit 279ed9b)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Google OAuth 2.0 sign-in end-to-end"
    expected: "Clicking 'Sign in with Google' redirects to Google, completes OAuth, returns to app at /, JWT stored in localStorage, user avatar and name appear in sidebar"
    why_human: "Requires a real GOOGLE_CLIENT_ID configured in .env, a live Google OAuth flow, and visual browser inspection"
  - test: "Sign-out and router guard redirect"
    expected: "Clicking Sign out in sidebar clears localStorage and redirects to /signin; navigating to / while unauthenticated also redirects to /signin"
    why_human: "Requires browser interaction to test localStorage clearing and navigation guard behavior"
  - test: "Dev-mode fallback without GOOGLE_CLIENT_ID"
    expected: "With GOOGLE_CLIENT_ID removed from .env and backend restarted, API calls to protected endpoints succeed as ANONYMOUS_USER_ID; frontend dev-mode experience is acceptable"
    why_human: "Requires restarting backend with modified .env and end-to-end browser verification of the dev-mode experience including the interaction between the frontend router guard and backend anonymous fallback"
---

# Phase 1003: Google Auth Backend JWT Middleware Verification Report

**Phase Goal:** Add Google OAuth 2.0 sign-in to the backend — verify Google ID tokens, upsert users into the DB, issue signed JWTs, and protect all /api/* endpoints with JWT middleware. Add a sign-in page and Vue Router auth guards to the frontend.
**Verified:** 2026-04-07T18:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (commit 279ed9b)

## Re-verification Summary

All 4 gaps from the initial verification are closed. Score moves from 11/12 to 12/12. No regressions found. The only remaining items are 3 human verification tests that were present in the initial verification and cannot be automated (live OAuth flow, browser localStorage inspection, dev-mode end-to-end UX).

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | POST /api/auth/google accepts an id_token and returns a JWT + user object | ✓ VERIFIED | `backend/routers/auth.py` google_auth() verifies token, upserts user, returns AuthResponse(jwt, user) |
| 2  | JWT contains user_id, email, name, picture, exp claims | ✓ VERIFIED | `backend/auth.py` create_jwt() builds payload with all 5 claims; 6 tests pass |
| 3  | decode_jwt() rejects expired or invalid tokens | ✓ VERIFIED | Catches ExpiredSignatureError + InvalidTokenError, raises ValueError; test_decode_jwt_expired_token passes |
| 4  | get_current_user() extracts user from Authorization: Bearer header | ✓ VERIFIED | `backend/auth.py` strips "Bearer " prefix, calls decode_jwt(), returns {id, email, name, picture} |
| 5  | Dev-mode fallback returns ANONYMOUS_USER_ID when no JWT provided and no GOOGLE_CLIENT_ID set | ✓ VERIFIED | test_get_current_user_no_auth_dev_mode passes; logic confirmed in auth.py |
| 6  | authStore stores JWT in localStorage and exposes isAuthenticated computed | ✓ VERIFIED | `authStore.ts` uses localStorage.setItem('jwt'), isAuthenticated = computed(() => !!jwt.value) |
| 7  | apiFetch() auto-adds Authorization: Bearer header to all API calls | ✓ VERIFIED | `apiFetch.ts` sets Authorization header from authStore.jwt before every fetch call |
| 8  | apiFetch() auto-redirects to /signin on 401 response | ✓ VERIFIED | `apiFetch.ts` checks res.status === 401, calls authStore.logout(), sets window.location.href = '/signin' |
| 9  | SignInView renders a centered card with Google Sign-In button | ✓ VERIFIED | `SignInView.vue` fetches /api/config for client_id, calls google.accounts.id.initialize + renderButton; styled with centered card |
| 10 | Vue Router guards redirect unauthenticated users to /signin | ✓ VERIFIED | `router/index.ts` beforeEach guard checks authStore.isAuthenticated, returns { path: '/signin' } if false |
| 11 | All /api/* endpoints (except /api/auth/google and /api/config) require a valid JWT | ✓ VERIFIED | `backend/routers/cv_convert.py` — `from backend.auth import get_current_user` at line 10; `user: dict = Depends(get_current_user)` on both get_cv_info() (line 20) and convert_cv() (line 43). All frontend views and components use apiFetch() — zero bare fetch() calls to protected endpoints. Only SignInView.vue uses bare fetch() and only to public endpoints /api/auth/google and /api/config (correct). |
| 12 | User's Google name and avatar display in the sidebar | ✓ VERIFIED | `AppSidebar.vue` has v-if="isAuthenticated && user" user-profile section with img (user.picture) and user.name; handleSignOut() calls authStore.logout() + router.push('/signin') |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/auth.py` | verify_google_token, create_jwt, decode_jwt, get_current_user | ✓ VERIFIED | All 4 functions present, substantive, wired via Depends() in router files |
| `backend/routers/auth.py` | POST /api/auth/google endpoint | ✓ VERIFIED | router prefix="/auth", google_auth() fully implemented with upsert + JWT |
| `backend/routers/cv_convert.py` | JWT-authenticated cv/info and cv/convert endpoints | ✓ VERIFIED | import at line 10; Depends(get_current_user) on both endpoints at lines 20 and 43 |
| `tests/test_auth.py` | 6 unit tests for JWT and get_current_user | ✓ VERIFIED | 6 tests, all pass: `6 passed, 8 warnings in 0.27s` |
| `frontend/src/stores/authStore.ts` | Auth state with jwt, user, isAuthenticated, login, logout | ✓ VERIFIED | Full Pinia setup-store, localStorage sync, exported useAuthStore |
| `frontend/src/utils/apiFetch.ts` | Fetch wrapper with Bearer token and 401 redirect | ✓ VERIFIED | Imports useAuthStore, sets Authorization header, handles 401 |
| `frontend/src/views/SignInView.vue` | Google Sign-In page UI | ✓ VERIFIED | Fetches /api/config and /api/auth/google via bare fetch() (correct — public endpoints); calls authStore.login on success |
| `frontend/src/views/SettingsView.vue` | GET/PUT /api/settings via apiFetch | ✓ VERIFIED | `import { apiFetch }` at line 3; GET call at line 35; PUT call at line 58 |
| `frontend/src/views/CvConverterView.vue` | POST /api/cv/convert and GET /api/config via apiFetch | ✓ VERIFIED | `import { apiFetch }` at line 4; config call at line 23; convert call at line 66 |
| `frontend/src/views/BaseCvView.vue` | GET /api/cv/info via apiFetch | ✓ VERIFIED | `import { apiFetch }` at line 4; call at line 13 |
| `frontend/src/router/index.ts` | Auth guards and /signin route | ✓ VERIFIED | /signin with meta.public, beforeEach dynamic-imports authStore, redirects on !isAuthenticated |
| `backend/routers/jobs.py` | JWT-authenticated job endpoints | ✓ VERIFIED | 8x Depends(get_current_user), user["id"] in all SQL |
| `backend/routers/settings.py` | JWT-authenticated settings endpoints | ✓ VERIFIED | 2x Depends(get_current_user), user["id"] in SELECT and INSERT |
| `backend/routers/cover_letter.py` | JWT-authenticated cover letter endpoints | ✓ VERIFIED | 3x Depends(get_current_user), user["id"] in all queries |
| `backend/routers/config.py` | Config endpoint with google_client_id field — intentionally public | ✓ VERIFIED | Returns google_client_id from GOOGLE_CLIENT_ID env var; no get_current_user (public as intended) |
| `frontend/src/stores/jobStore.ts` | All API calls use apiFetch | ✓ VERIFIED | 11x apiFetch() calls, 0x bare fetch() calls |
| `frontend/src/components/AppSidebar.vue` | User profile display and sign-out button | ✓ VERIFIED | useAuthStore, user-profile div, user-avatar img, sign-out-btn, handleSignOut function |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/routers/auth.py` | `backend/auth.py` | imports verify_google_token, create_jwt | ✓ WIRED | `from backend.auth import create_jwt, verify_google_token` confirmed |
| `backend/routers/cv_convert.py` | `backend/auth.py` | Depends(get_current_user) | ✓ WIRED | `from backend.auth import get_current_user` at line 10; both endpoints wired at lines 20 and 43 |
| `backend/auth.py` | `backend/db.py` | ANONYMOUS_USER_ID constant | ✓ WIRED | `from backend.db import ANONYMOUS_USER_ID` confirmed |
| `frontend/src/utils/apiFetch.ts` | `frontend/src/stores/authStore.ts` | imports useAuthStore to read jwt | ✓ WIRED | `import { useAuthStore } from '@/stores/authStore'` confirmed |
| `frontend/src/router/index.ts` | `frontend/src/stores/authStore.ts` | beforeEach guard checks isAuthenticated | ✓ WIRED | Dynamic import of useAuthStore inside beforeEach, checks authStore.isAuthenticated |
| `frontend/src/views/SignInView.vue` | `frontend/src/stores/authStore.ts` | login() action after Google callback | ✓ WIRED | authStore.login(data.jwt, data.user) called after POST /api/auth/google success |
| `frontend/src/views/SettingsView.vue` | `frontend/src/utils/apiFetch.ts` | apiFetch for GET/PUT /api/settings | ✓ WIRED | import at line 3; calls at lines 35 and 58 |
| `frontend/src/views/CvConverterView.vue` | `frontend/src/utils/apiFetch.ts` | apiFetch for POST /api/cv/convert | ✓ WIRED | import at line 4; convert call at line 66 |
| `frontend/src/views/BaseCvView.vue` | `frontend/src/utils/apiFetch.ts` | apiFetch for GET /api/cv/info | ✓ WIRED | import at line 4; call at line 13 |
| `frontend/src/stores/jobStore.ts` | `frontend/src/utils/apiFetch.ts` | import apiFetch | ✓ WIRED | `import { apiFetch } from '@/utils/apiFetch'` at line 4 |
| `frontend/src/components/AppSidebar.vue` | `frontend/src/stores/authStore.ts` | useAuthStore() for user profile | ✓ WIRED | useAuthStore imported and used for user, isAuthenticated, handleSignOut |
| `backend/routers/jobs.py` | `backend/auth.py` | Depends(get_current_user) | ✓ WIRED | 8 occurrences confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `backend/routers/jobs.py` list_jobs | jobs rows | `SELECT * FROM jobs WHERE user_id=?` with user["id"] from JWT | Yes — user-scoped DB query | ✓ FLOWING |
| `backend/routers/cv_convert.py` get_cv_info | cv data | load_base_cv() reads base_cv.yaml from disk | Yes — reads real YAML file | ✓ FLOWING |
| `frontend/src/views/SignInView.vue` | google_client_id | `GET /api/config` then GOOGLE_CLIENT_ID env var | Yes — reads env var, shows error if empty | ✓ FLOWING |
| `frontend/src/components/AppSidebar.vue` | user, isAuthenticated | authStore (ref from localStorage + login()) | Yes — populated on login, persisted across reloads | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 6 auth tests (regression check) | `uv run pytest tests/test_auth.py -v` | 6 passed, 8 warnings in 0.27s | ✓ PASS |
| cv_convert.py auth import present | grep get_current_user in cv_convert.py | line 10: import; line 20: Depends; line 43: Depends | ✓ PASS |
| SettingsView uses apiFetch | grep apiFetch in SettingsView.vue | import at line 3; calls at lines 35 and 58 | ✓ PASS |
| CvConverterView uses apiFetch | grep apiFetch in CvConverterView.vue | import at line 4; calls at lines 23 and 66 | ✓ PASS |
| BaseCvView uses apiFetch | grep apiFetch in BaseCvView.vue | import at line 4; call at line 13 | ✓ PASS |
| No bare fetch() to protected endpoints in views | grep "fetch(" in frontend/src/views/*.vue | Only SignInView.vue lines 45 and 67 — both to public endpoints | ✓ PASS |
| No bare fetch() in components | grep "fetch(" in frontend/src/components/*.vue | No matches | ✓ PASS |
| Commit 279ed9b exists | git show --stat 279ed9b | fix(1003): close verification gap — 6 files changed confirmed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| AUTH-01 | 1003-01 | User can sign in using their Google account | ✓ SATISFIED | `backend/routers/auth.py` POST /api/auth/google calls verify_google_token(); SignInView.vue initializes GSI and calls /api/auth/google |
| AUTH-02 | 1003-01 | Backend verifies Google ID token and issues a signed JWT stored in localStorage | ✓ SATISFIED | google.oauth2.id_token.verify_oauth2_token() in auth.py; authStore.ts stores JWT in localStorage.setItem('jwt') |
| AUTH-03 | 1003-03 | All /api/* endpoints require a valid JWT (middleware returns 401 if missing/invalid) | ✓ SATISFIED | All protected endpoints have Depends(get_current_user): jobs (8x), settings (2x), cover_letter (3x), cv_convert (2x — added in commit 279ed9b). All frontend views and components use apiFetch() to send Bearer tokens. Public exceptions /api/auth/google and /api/config are intentionally exempt. |
| AUTH-04 | 1003-02 | Frontend Vue Router guards redirect unauthenticated users to the sign-in page | ✓ SATISFIED | `router/index.ts` beforeEach guard redirects to /signin when !authStore.isAuthenticated |
| AUTH-05 | 1003-02 | User can sign out, which clears the JWT from localStorage | ✓ SATISFIED | authStore.logout() removes 'jwt' and 'auth_user' from localStorage; handleSignOut() in AppSidebar calls this |
| AUTH-06 | 1003-03 | User's name and profile picture from Google are displayed in the app header/sidebar | ✓ SATISFIED | AppSidebar.vue user-profile section with img (user.picture) + referrerpolicy="no-referrer" and user.name displayed |

### Anti-Patterns Found

None. All previously flagged bare fetch() calls to protected endpoints have been migrated to apiFetch(). The only remaining bare fetch() calls are in SignInView.vue (lines 45 and 67) which target public endpoints `/api/auth/google` and `/api/config` — no Bearer token is appropriate here since these are used before authentication.

### Human Verification Required

#### 1. Google OAuth 2.0 Sign-In Flow

**Test:** Configure GOOGLE_CLIENT_ID and JWT_SECRET in .env. Start backend (`uv run uvicorn backend.main:app --reload`) and frontend (`npm run dev`). Open http://localhost:5173. Confirm redirect to /signin. Click "Sign in with Google". Complete the Google OAuth consent.
**Expected:** After completing OAuth, browser lands on / with JWT in localStorage. Sidebar shows Google avatar and display name.
**Why human:** Requires a real Google Cloud project with OAuth 2.0 Client ID configured, a live browser OAuth flow, and visual inspection of the sidebar user profile.

#### 2. Sign-Out and Router Guard Redirect

**Test:** After signing in, click "Sign out" in the sidebar. Then try navigating to http://localhost:5173/ directly.
**Expected:** Sign-out clears localStorage ('jwt' and 'auth_user' keys removed), redirects to /signin. Direct navigation to / while unauthenticated redirects to /signin.
**Why human:** Requires browser interaction to observe localStorage state changes and navigation redirect behavior.

#### 3. Dev-Mode Fallback Without Google Credentials

**Test:** Remove GOOGLE_CLIENT_ID from .env (leave it commented out). Restart the backend. Open http://localhost:5173.
**Expected:** The sign-in page shows "Google Sign-In is not configured." API calls to protected endpoints succeed as ANONYMOUS_USER_ID. Note: the frontend router guard checks `authStore.isAuthenticated` (whether JWT is in localStorage), not whether GOOGLE_CLIENT_ID is set — the interaction between the frontend guard and the backend anonymous fallback requires human judgment about acceptable dev-mode UX.
**Why human:** Requires restarting backend with modified .env and end-to-end browser verification.

### Gaps Summary

No gaps. All 12 truths are verified. Commit 279ed9b closed every item from the initial verification:

1. `backend/routers/cv_convert.py` — `get_current_user` import and `Depends(get_current_user)` added to both GET /api/cv/info and POST /api/cv/convert. AUTH-03 is now fully satisfied on the backend.
2. `frontend/src/views/SettingsView.vue` — both fetch() calls migrated to apiFetch().
3. `frontend/src/views/CvConverterView.vue` — fetch() calls migrated to apiFetch().
4. `frontend/src/views/BaseCvView.vue` — fetch() call migrated to apiFetch().
5. `frontend/src/components/CoverLetterSection.vue` and `frontend/src/components/RegeneratePanel.vue` — also migrated as part of the same commit.

The phase goal is achieved. Only the 3 human verification items (live OAuth flow, browser interactions) remain outstanding.

---

_Verified: 2026-04-07T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
