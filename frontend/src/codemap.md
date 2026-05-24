# frontend/src/

## Responsibility

This is the **application source root** — the heart of the CV Maker SPA. It contains the Vue app bootstrap (`main.ts`), the root shell component (`App.vue`), the shared TypeScript type definitions (`types.ts`), and organizes all feature modules (views, stores, components, router) under a clean directory structure. Every file in this tree runs in the browser context (DOM APIs, Vue runtime, Vite-bundled modules).

## Design

### Bootstrap (`main.ts`)

The app is created with the standard Vue 3 pattern: `createApp(App)` → install `Pinia` → install `Router` → mount to `#app`. The order is critical — Pinia **must** be installed before the router because the router's `beforeEach` guard dynamically imports and reads from the auth store.

### Root Component (`App.vue`)

`App.vue` serves as the **application shell** with two distinct layouts controlled by authentication state:

1. **Unauthenticated** (`!authStore.isAuthenticated`) → `signin-layout`: centered full-viewport layout that displays only the `<RouterView />` (renders `SignInView`).
2. **Authenticated** → `app-shell`: a **CSS Grid sidebar layout** (`260px sidebar + 1fr main content`). Includes:
   - `AppSidebar` component — collapsible navigation sidebar.
   - Sidebar toggle (hamburger/close SVG icons) — visible on mobile (`≤768px`).
   - `sidebar-overlay` — dark backdrop when sidebar is open on mobile.
   - `<RouterView />` — renders the active route component inside `<main>`.

**Responsive behavior**: On viewports `≤768px`, the grid collapses to a single column, the sidebar becomes an off-canvas overlay, and a floating toggle button appears. Route changes automatically close the sidebar via a `watch` on `route.fullPath`.

### Type System (`types.ts`)

The central type definitions for the entire application — shared between views, stores, and API consumers:

| Type/Interface           | Purpose                                                    |
|--------------------------|------------------------------------------------------------|
| `ContactInfo`            | Personal details (name, email, phone, linkedin, github, location, work auth) |
| `BaseCV`                 | The user's master CV structure (contact, summary, experience, skills, education, projects, certs, languages) |
| `ExperienceItem`         | A single work experience entry (company, title, dates, bullets, technologies) |
| `EducationItem`          | An education entry (institution, degree, field, year)      |
| `ProjectItem`            | A personal/academic project (name, description, technologies, url) |
| `LanguageItem`           | Language proficiency (language name + level)               |
| `TailoredCV`             | A CV version tailored for a specific job — extends `BaseCV` structure with `highlighted_technologies` and `tailoring_notes` |
| `TailoringNote`          | A single change made during tailoring: section affected, what changed, why, action type (modified/added/removed/reordered/unchanged) |
| `JobResponse`            | Full API response for a job — includes company info, status, tailored CV, gap analysis, PDF URL, cover letter, and version history |
| `JobCreate`              | Payload for creating a new job (company name, job text/link, model selection, creativity level) |
| `GapItem`                | A single skill/requirement gap: requirement text, match level (strong/partial/missing), evidence |
| `CvHistoryEntry` / `ClHistoryEntry` | Versioned history records for CV and cover letter iterations |
| `JobStatus`              | Union type: `'pending' | 'running' | 'complete' | 'failed' | 'cancelled'` |
| `MatchLevel`             | Union type: `'strong' | 'partial' | 'missing'`            |

### Global Routing (`src/router/index.ts`)

The Vue Router instance uses **HTML5 history mode** (`createWebHistory`) with six routes:

| Path             | Component          | Lazy? | Public? | Purpose                                  |
|------------------|--------------------|-------|---------|------------------------------------------|
| `/signin`        | `SignInView`       | Yes   | Yes     | Google Sign-In page                      |
| `/`              | `JobFormView`      | No    | No      | Home — submit a new job for CV tailoring |
| `/jobs/:id`      | `JobDetailView`    | No    | No      | View tailored CV, gap analysis, PDF, cover letter for a specific job |
| `/convert`       | `CvConverterView`  | Yes   | No      | Convert CV to PDF (standalone converter) |
| `/base-cv`       | `BaseCvView`       | Yes   | No      | Edit the user's master/base CV           |
| `/settings`      | `SettingsView`     | Yes   | No      | User preferences and account settings    |

**Route guard** (`beforeEach`): Runs before every navigation. Dynamically imports the auth store (to avoid circular dependency at module parse time). Redirects unauthenticated users to `/signin` unless the target route has `meta.public: true`.

**Code-splitting**: Four views use dynamic `() => import(...)` to create separate chunks, reducing initial bundle size. The two direct imports (`JobFormView`, `JobDetailView`) are in the critical path and bundled with the main chunk.

### State Management

**Pinia** is the single global state management solution. Stores are located under `src/stores/` and are lazily discovered by components via `useXxxStore()` composables. The key store is:

- **`authStore`** (`src/stores/authStore.ts`): Manages Google authentication state (`isAuthenticated`, user info, credential token). Consumed by `App.vue` (to toggle shell layout) and the router guard (to enforce authentication).

## Flow

### Data & Control Flow

```
User Action → View Component → Pinia Store / direct fetch → API (via /api proxy → backend)
                ↓
    UI Update ← Reactive state ← Store / local ref     ← API Response (JobResponse, BaseCV, etc.)
```

1. **Auth**: Google GSI popup → credential token → sent to backend → auth store updated → router guard allows navigation → shell layout rendered.
2. **Job Submission**: `JobFormView` → `POST /api/jobs` with `JobCreate` payload → backend processes → returns `JobResponse` with status `'pending'` → poll until `'complete'` → display `TailoredCV` and `GapItem[]`.
3. **Base CV Editing**: `BaseCvView` fills a form from `BaseCV` (fetched from `/api/base-cv`) → user edits → `PUT /api/base-cv` → updated.
4. **PDF/Conversion**: `CvConverterView` sends CV data → `POST /api/pdf` → receives PDF blob/URL.
5. **CV/CL History**: `JobDetailView` displays `cv_history: CvHistoryEntry[]` and `cl_history: ClHistoryEntry[]` for version tracking.

### View Composition Pattern

Each view follows a consistent pattern:
- `<script setup lang="ts">` for logic
- Uses Pinia stores via `useXxxStore()`
- Calls the backend via `fetch` to `/api/*` (proxied by Vite)
- Renders results with Vue's template syntax and reactive bindings

## Integration

### Internal Module Boundaries

```
src/
├── main.ts                 ← Bootstrap, creates Vue app
├── App.vue                 ← Root shell (auth-aware layout, sidebar, router outlet)
├── types.ts                ← Shared TypeScript interfaces (API contracts)
├── router/
│   └── index.ts            ← Route definitions + auth guard
├── stores/
│   └── authStore.ts        ← Authentication state (Pinia)
├── views/
│   ├── JobFormView.vue     ← Job submission form
│   ├── JobDetailView.vue   ← Job result + tailored CV viewer
│   ├── BaseCvView.vue      ← Master CV editor
│   ├── CvConverterView.vue ← Standalone CV-to-PDF converter
│   ├── SettingsView.vue    ← User preferences
│   └── SignInView.vue      ← Google Sign-In page
├── components/
│   └── AppSidebar.vue      ← Navigation sidebar (used by App.vue)
└── ... (additional feature components)
```

### External Integration Points

| Boundary              | Interface                                          | Direction       |
|-----------------------|----------------------------------------------------|-----------------|
| Backend API           | REST over `/api/*` (proxied by Vite dev server)    | Outbound        |
| Google Identity       | GSI client (`accounts.google.com/gsi/client`)      | Outbound        |
| Browser DOM           | `#app` mount point in `index.html`                 | Render target   |
| Vite tooling          | HMR, TypeScript transpilation, CSS injection       | Build-time      |

### Key Symbols & APIs

| Symbol                          | Location              | Role                                            |
|---------------------------------|-----------------------|-------------------------------------------------|
| `createApp()`                   | `main.ts`             | Creates the Vue application instance            |
| `createPinia()`                 | `main.ts` (via pinia) | Creates the Pinia state management instance     |
| `router`                        | `router/index.ts`     | Exported Vue Router instance with auth guard    |
| `useAuthStore()`                | `stores/authStore.ts` | Pinia store composable for auth state           |
| `useRoute()`                    | `App.vue` (vue-router)| Reactive access to current route (sidebar close)|
| `ContactInfo`, `BaseCV`, etc.   | `types.ts`            | Core data model interfaces                      |
| `JobResponse`, `JobCreate`      | `types.ts`            | API request/response contracts                  |
| `TailoredCV`, `TailoringNote`   | `types.ts`            | LLM tailoring result types                      |
| `GapItem`, `MatchLevel`         | `types.ts`            | Skill gap analysis types                        |
| `JobStatus`                     | `types.ts`            | Job lifecycle state machine                     |
| `CvHistoryEntry`, `ClHistoryEntry` | `types.ts`         | Version history records                         |
