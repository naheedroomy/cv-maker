# frontend/src/stores/

## Responsibility

Pinia state management covering authentication, job sessions, and the user's base CV. All stores follow the Composition API (`setup store`) pattern. API calls are delegated to the `apiFetch` wrapper, never to raw `fetch`.

## Design Patterns

- **Pinia setup stores** (Composition API style) — each store exports a `defineStore` call with refs and actions
- **Optimistic updates**: `toggleApplied`, `cancelJob`, `saveCoverLetter` update local state immediately then sync with server
- **SSE + polling fallback**: `jobStore.openSSE` opens a server-sent events stream for real-time job status; on `onerror` it falls back to 3s polling until a terminal status
- **`apiFetch` wrapper**: all stores use the shared utility for auth header injection and 401 handling
- **JWT persistence**: `authStore` restores from `localStorage` on creation, validates expiry

---

## Stores

### `authStore.ts` — Authentication

**State**: `jwt` (string|null), `user` (AuthUser|null), `isAuthenticated` (computed)

**Actions**:
- `login(token, userData)`: Stores JWT and user in both reactive state and localStorage
- `logout()`: Clears state + localStorage
- **Initialization**: On store creation, reads `jwt` from localStorage, decodes payload to check `exp`; if expired, clears storage

**Edge cases**: Handles URL-safe base64 (PyJWT format with `-` and `_`); handles corrupt localStorage data gracefully

### `jobStore.ts` — Job Sessions

**State**: `jobs` (JobResponse[]), `currentJob` (JobResponse|null), `error` (string|null)

**Key Actions**:
- `fetchJobs()`: GET `/api/jobs`, sorts newest-first. Polled every 30s by `AppSidebar`
- `fetchJob(id)`: GET `/api/jobs/:id`, updates both `currentJob` and the corresponding entry in `jobs[]`
- `submitJob(payload)`: POST `/api/jobs`, prepends new job to `jobs[]`, returns `job.id`
- `cancelJob(id)`: DELETE `/api/jobs/:id`, optimistically sets status to `cancelled`, closes SSE
- `toggleApplied(id)`: PATCH `/api/jobs/:id/applied`, full object replacement from server response
- `deleteJob(id)`: DELETE `/api/jobs/:id/remove`, removes from `jobs[]`, clears `currentJob`
- `regenerateJob(job, model?, creativityLevel?)`: POST `/api/jobs/:id/regenerate`, replaces with server response
- `downloadPdf(jobId, companyName, version?)`: GET PDF blob, triggers browser download. Checks `cv_filename` setting for filename
- `openSSE(jobId)`: Opens `EventSource` at `/api/jobs/:id/events`. Listens for `status` events (partial updates) and `complete` event (full re-fetch). Falls back to 3s polling on error
- `closeSSE()`: Closes SSE and clears polling interval
- `generateCoverLetter(jobId, model, tone, userNotes)`: POST `/api/jobs/:id/cover-letter`, polls up to 60×3s for result
- `saveCoverLetter(jobId, text, notes)`: PUT `/api/jobs/:id/cover-letter`
- `downloadCoverLetterPdf(jobId, companyName)`: GET PDF blob

**SSE details**: Internal `_sse` and `_pollInterval` are plain `let` bindings (not refs — they are implementation details, not UI-reactive). SSE `complete` event triggers a full `fetchJob` because SSE payloads are partial and may miss cover letter or history fields.

### `cvStore.ts` — Base CV

**State**: `cv` (BaseCV|null), `loading`, `saving`, `uploading`, `error`, `uploadProgress`

**Actions**:
- `fetchCv()`: GET `/api/cv/me`, nulls `cv` if `has_cv` is false
- `saveCv()`: PUT `/api/cv/me` with full CV JSON
- `deleteCv()`: DELETE `/api/cv/me`
- `uploadPdf(file)`: POST `/api/cv/upload` as FormData (no manual Content-Type — browser sets multipart boundary)
- `createEmptyCv()`: Initializes a `BaseCV` with empty fields for all sections

## Data & Control Flow

```
User Action → Store Action → apiFetch() → Backend API
                                    ↓
                              On 401: logout + redirect /signin
                                    ↓
                          Store updates reactive state
                                    ↓
                    Vue components reactively re-render
```

**SSE flow (job generation)**:
```
JobDetailView.loadJob(id) → store.fetchJob(id) → if not terminal → store.openSSE(id)
  SSE 'status' → partial update currentJob
  SSE 'complete' → closeSSE, fetchJob(id) for full state
  SSE onerror → fallback polling every 3s until terminal status
```

## Integration Points

- **`apiFetch`**: All store actions use this — it injects `Authorization: Bearer <jwt>` and handles 401
- **`authStore`** ↔ `apiFetch`: `apiFetch` reads `authStore.jwt` and calls `authStore.logout()` on 401
- **`jobStore`** ↔ `AppSidebar.vue`: Sidebar mounts, calls `fetchJobs()`, polls every 30s
- **`jobStore`** ↔ `JobDetailView.vue`: View manages SSE lifecycle via `openSSE`/`closeSSE`
- **`cvStore`** ↔ `BaseCvView.vue`: View binds to `cv`, `loading`, `saving`, `uploading`, `uploadProgress` refs
