---
phase: "07"
plan: "01"
subsystem: frontend
tags: [vue3, vite, pinia, vue-router, typescript, sse, fetch]
dependency_graph:
  requires: []
  provides:
    - frontend/src/types.ts (TypeScript interfaces matching backend API contract)
    - frontend/src/stores/jobStore.ts (Pinia store with SSE lifecycle)
    - frontend/src/router/index.ts (Vue Router with / and /jobs/:id routes)
    - frontend/src/App.vue (CSS Grid shell: 260px sidebar + 1fr main)
    - frontend/vite.config.ts (Vite dev server with /api proxy to localhost:8000)
  affects:
    - "07-02 (JobFormView, JobDetailView depend on this store and router)"
    - "07-03 (all components depend on types and store)"
tech_stack:
  added:
    - vue@3.5.31 (UI framework)
    - pinia@3.0.4 (state management)
    - vue-router@5.0.4 (client-side routing)
    - vite@8.0.3 (dev server + build tool)
    - "@vitejs/plugin-vue@6.0.5 (Vite plugin for .vue SFC compilation)"
    - typescript@6.0.2 (type safety)
    - vue-tsc@3.2.6 (TypeScript checker for Vue SFCs)
  patterns:
    - Pinia setup store (defineStore with ref + functions, not options API)
    - EventSource with named event listeners (status/complete) — not onmessage
    - Native fetch — no axios (permanently excluded per CLAUDE.md)
    - CSS Grid layout (260px 1fr) with scoped CSS per component — no Tailwind
    - Blob URL download pattern (createObjectURL + revokeObjectURL)
key_files:
  created:
    - frontend/package.json
    - frontend/vite.config.ts
    - frontend/tsconfig.json
    - frontend/tsconfig.app.json
    - frontend/tsconfig.node.json
    - frontend/index.html
    - frontend/env.d.ts
    - frontend/src/main.ts
    - frontend/src/types.ts
    - frontend/src/stores/jobStore.ts
    - frontend/src/router/index.ts
    - frontend/src/App.vue
    - frontend/src/views/JobFormView.vue
    - frontend/src/views/JobDetailView.vue
    - frontend/src/components/AppSidebar.vue
  modified: []
decisions:
  - "Named export `router` from router/index.ts (not default) — matches main.ts import pattern"
  - "Separate _sidebarInterval from _pollInterval — sidebar polling and SSE fallback polling are independent concerns"
  - "Jobs sorted by created_at descending in fetchJobs — UI-SPEC requirement enforced at store level"
  - "Scaffold leftover files (HomeView, AboutView, HelloWorld, counter store) removed — keep src clean"
metrics:
  duration: "269s"
  completed: "2026-04-04T14:23:38Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 15
  files_modified: 0
  commits: 2
---

# Phase 7 Plan 01: Vue 3 Project Scaffold + Foundation Layer Summary

**One-liner:** Vue 3 SPA scaffolded with Vite proxy to FastAPI, Pinia store with SSE lifecycle + fallback polling, Vue Router with createWebHistory, and CSS Grid shell (260px sidebar + 1fr main).

---

## What Was Built

### Task 1 — Scaffold Vue 3 project and configure Vite proxy

Scaffolded a Vue 3 SPA into `frontend/` using `npm create vue@latest` with TypeScript, Pinia, and Vue Router. Updated vite.config.ts to proxy `/api/*` requests to `http://localhost:8000` without any path rewrite (backend already uses `/api` prefix). Updated `index.html` title to "CV Maker". Cleaned up `main.ts` to use named `router` import. Removed default CSS assets (base.css, main.css, logo.svg) — using scoped CSS throughout.

**Commit:** 191b8a6

### Task 2 — TypeScript types, Pinia store, Vue Router, App.vue shell

Created all foundational source files:

- **`src/types.ts`** — Full TypeScript interfaces matching backend API contract: `ContactInfo`, `ExperienceItem`, `EducationItem`, `ProjectItem`, `TailoredCV`, `GapItem`, `JobStatus`, `JobResponse`, `JobCreate`

- **`src/stores/jobStore.ts`** — Pinia setup store with:
  - `fetchJobs()`, `fetchJob()`, `submitJob()`, `cancelJob()`, `downloadPdf()` actions
  - `openSSE(jobId)` using named event listeners (`addEventListener('status', ...)`, `addEventListener('complete', ...)`) — NOT `onmessage`
  - Relative EventSource URL (`/api/jobs/${jobId}/events`) — no hardcoded localhost
  - Fallback polling (5s) on SSE error, cleared on terminal status
  - Sidebar polling (30s) via `startSidebarPolling()` / `stopSidebarPolling()`
  - `URL.revokeObjectURL()` after PDF download blob
  - `_sse` and `_pollInterval` as plain `let` variables (not reactive)

- **`src/router/index.ts`** — `createWebHistory()` with named export `router`, routes for `/` and `/jobs/:id`

- **`src/App.vue`** — CSS Grid shell: `grid-template-columns: 260px 1fr`, `min-width: 640px`, system-ui font stack, `#f8f9fa` background

- **Stub views:** `JobFormView.vue`, `JobDetailView.vue` (minimal templates, prevent router import errors)

- **Stub component:** `AppSidebar.vue` (sticky sidebar with white background and border)

**Commit:** 4e30757

---

## Verification Results

- `npx vue-tsc --noEmit` — exits with code 0 (zero type errors)
- All dependencies present: vue, pinia, vue-router, vite (no Tailwind)
- Vite proxy `/api` → `http://localhost:8000` configured (no rewrite)
- EventSource uses relative URL, named event listeners, fallback polling
- CSS Grid layout: 260px sidebar + 1fr main, min-width 640px

---

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Minor Adjustments (not deviations)

1. **Scaffold included vite-plugin-vue-devtools** — The plan said "DevTools: No" during the npm create vue prompt, but the CLI version (create-vue@3.22.2) added it anyway. The plugin was removed from `vite.config.ts` (not imported). The package entry remains in `package.json` but does not affect functionality. Can be removed via `npm uninstall vite-plugin-vue-devtools` if desired.

2. **Separate _sidebarInterval added to store** — The plan mentioned `startSidebarPolling`/`stopSidebarPolling` but Pattern 6 in RESEARCH.md suggested managing it inside AppSidebar.vue. The store approach was used for cleaner interface and to match the exported API listed in the plan's acceptance criteria. Both approaches are valid; the store approach keeps all interval management in one place.

3. **Leftover scaffold files removed** — `HomeView.vue`, `AboutView.vue`, `HelloWorld.vue`, `TheWelcome.vue`, `WelcomeItem.vue`, `counter.ts`, icons directory, `.vscode/` were removed to keep src/ clean.

---

## Known Stubs

The following files are intentional stubs for this plan (will be fully implemented in 07-02 and 07-03):

| File | Stub | Reason |
|------|------|--------|
| `frontend/src/views/JobFormView.vue` | Static placeholder text | Will be replaced with full form in 07-02 |
| `frontend/src/views/JobDetailView.vue` | Static placeholder text | Will be replaced with status/preview in 07-02 |
| `frontend/src/components/AppSidebar.vue` | "No sessions yet" hardcoded | Will be replaced with real session list in 07-03 |

These stubs are intentional and do not prevent the plan's goal (running dev server with router and store). They will be resolved in subsequent plans (07-02, 07-03).

---

## Self-Check: PASSED

All 12 key files confirmed present on disk. Both task commits (191b8a6, 4e30757) verified in git log. TypeScript check (`vue-tsc --noEmit`) exits 0.
