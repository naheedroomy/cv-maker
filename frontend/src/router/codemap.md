# frontend/src/router/

## Responsibility

Application routing and authentication guard. Defines all navigable pages, lazy-loads non-critical views, and enforces that unauthenticated users are redirected to `/signin`.

## Design

- **Vue Router** with `createWebHistory` (clean URLs, no hash)
- **Lazy loading**: `CvConverterView`, `BaseCvView`, `SettingsView`, and `SignInView` use dynamic `import()` for code splitting
- **Navigation guard** (`router.beforeEach`) dynamically imports `useAuthStore` to avoid Pinia-initialization circular dependency
- **Public route flag**: `meta: { public: true }` on `/signin` bypasses the auth guard

## Flow

1. Every route transition triggers `beforeEach`
2. Guard loads `authStore` and checks `isAuthenticated`
3. If `to.meta.public` → allowed regardless
4. If not authenticated → redirect to `/signin`
5. Otherwise → proceed

## Integration

- **Pinia**: Guard dynamically imports `authStore` (deferred import avoids circular dependency with `main.ts` where Pinia is created)
- **App.vue**: Uses `<RouterView />` in both authenticated (sidebar + main) and unauthenticated (centered card) layouts
- **Components**: `AppSidebar.vue` uses `router.push` for navigation; `SessionEntry.vue` uses `<router-link>` for session links

## Routes

| Path | Component | Lazy | Auth Required | Purpose |
|---|---|---|---|---|
| `/signin` | SignInView | Yes | No (public) | Google Sign-In |
| `/` | JobFormView | No | Yes | Submit new job description |
| `/jobs/:id` | JobDetailView | No | Yes | View/manage a job session (CV, cover letter, analysis) |
| `/convert` | CvConverterView | Yes | Yes | Import base CV from text/file via AI |
| `/base-cv` | BaseCvView | Yes | Yes | Edit base CV (upload PDF or fill manually) |
| `/settings` | SettingsView | Yes | Yes | Configure AI providers, API keys, model names |
