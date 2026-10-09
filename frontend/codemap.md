# frontend/

## Responsibility

This is the **CV Maker Single-Page Application** — a Vue 3 + TypeScript frontend that provides the UI for creating, tailoring, and managing CVs/jobs. It runs entirely in the browser and communicates with a Python backend at `localhost:8000` via REST APIs under the `/api` prefix. The app handles user authentication via Google Sign-In, job submission with LLM-driven CV tailoring, base-CV management, and PDF conversion.

## Design

### Architectural Patterns

- **Vue 3 Composition API** with `<script setup>` — the sole component authoring pattern. No Options API.
- **Pinia** for global state management (stores live under `src/stores/`), providing reactive auth state and user data.
- **Vue Router** for SPA routing with guards — routes are defined in `src/router/index.ts`; the `beforeEach` guard enforces authentication on all non-public routes.
- **Vite 8** as the build tool — fast HMR, TypeScript transpilation via `esbuild`, production bundling via Rollup. The dev server proxies `/api` requests to the backend.
- **Lazy-loaded views** — `CvConverterView`, `BaseCvView`, `SettingsView`, and `SignInView` use dynamic `import()` for code-splitting at the route level.

### Configuration Strategy

- **Dual tsconfig**: `tsconfig.app.json` targets the browser (DOM APIs, Vue SFC support) with `@vue/tsconfig` base and `@/*` path alias. `tsconfig.node.json` targets Node.js tooling (Vite config, Vitest, etc.) with `@tsconfig/node24` base.
- **No emit**: TypeScript is used purely for type-checking via `vue-tsc --build`. Transpilation is handled by Vite's `esbuild`.
- **Incremental builds**: `.tsbuildinfo` files are written to `node_modules/.tmp/` to avoid polluting the project root.

## Flow

### App Bootstrap Sequence

```
index.html (HTML entry point)
  └── <script type="module" src="/src/main.ts">
        ├── createApp(App)
        ├── app.use(createPinia())        // Initialize state management
        ├── app.use(router)               // Initialize routing + auth guard
        └── app.mount('#app')             // Attach to <div id="app">
```

### Authentication Flow

1. `SignInView.vue` fetches the public configuration, then loads `https://accounts.google.com/gsi/client` on demand and waits for its `load` event (or uses the already-loaded SDK). Script failures/timeouts and configuration failures offer an in-page retry.
2. Only after the SDK is ready, `SignInView.vue` initializes and renders the Google sign-in button and handles the credential callback. `tests/browser/google-signin.mjs` exercises delayed/failed/cached script loading, configuration retry, and the token exchange with mocked Google/API responses.
3. On successful sign-in, `authStore` updates its reactive `isAuthenticated` state.
4. The `beforeEach` router guard checks `authStore.isAuthenticated` on every navigation:
   - Public routes (`meta.public: true`) pass through regardless (currently only `/signin`).
   - All other routes redirect to `/signin` if not authenticated.
   - The guard uses a **dynamic `import()`** for the auth store to avoid circular dependencies (Pinia must be created before the router guard can access it).

### API Interaction

All `/api/*` requests are proxied through the Vite dev server to `http://localhost:8000` with `changeOrigin: true`. The backend already uses the `/api` prefix, so no URL rewrite is applied. In production, the built SPA is served statically and the same proxy logic is expected to be handled by the deployment layer (e.g., nginx or the Python server).

## Integration

### External Dependencies

| Dependency           | Purpose                                              |
|----------------------|------------------------------------------------------|
| `vue` (3.5)          | Progressive UI framework                             |
| `vue-router` (5.0)   | Client-side SPA routing                              |
| `pinia` (3.0)        | Reactive state management                            |
| `vite` (8.0)         | Build tool and dev server                            |
| `@vitejs/plugin-vue` | Vite plugin for Vue SFC compilation                  |
| `vue-tsc` (3.2)      | TypeScript type-checking for `.vue` files            |
| Google GSI           | Google Sign-In for user authentication               |

### Backend Integration Points

| Frontend Concern           | Backend Endpoint (proxied) | Notes                                       |
|----------------------------|---------------------------|---------------------------------------------|
| Job creation & CV tailoring| `/api/jobs`               | POST: submits company name + job text + model/creativity params |
| Job listing & status       | `/api/jobs`               | GET: polls job status, retrieves tailored CV |
| Job detail                 | `/api/jobs/:id`           | GET: single job result with gap diff, CV history |
| Base CV management         | `/api/base-cv`            | CRUD operations on the user's master CV     |
| PDF generation             | `/api/pdf`                | CV-to-PDF conversion                        |
| User settings              | `/api/settings`           | User preferences, default model/language    |

### Key Files

| File                      | Role                                                  |
|---------------------------|-------------------------------------------------------|
| `index.html`              | HTML entry point; mounts Vue app    |
| `package.json`            | Dependencies, scripts (`dev`, `build`, `type-check`)  |
| `vite.config.ts`          | Vite config: Vue plugin, `@` alias, API proxy, build  |
| `tsconfig.json`           | Project references to `tsconfig.app.json` and `tsconfig.node.json` |
| `tsconfig.app.json`       | TS config for browser/app code (Vue DOM, `@/*` paths) |
| `tsconfig.node.json`      | TS config for tooling code (Node.js, `bundler` mode)  |
| `env.d.ts`                | Vite client type declarations (`/// <reference types="vite/client" />`) |
