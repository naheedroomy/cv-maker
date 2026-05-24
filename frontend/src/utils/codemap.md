# frontend/src/utils/

## Responsibility

Shared utility functions used across the frontend application. Currently a single module: the API fetch wrapper.

## Design

### `apiFetch.ts` — Authenticated Fetch Wrapper

A drop-in replacement for native `fetch()` for all `/api/*` calls.

**Behavior**:
1. Reads JWT from `authStore`
2. Adds `Authorization: Bearer <jwt>` header to every request
3. Auto-sets `Content-Type: application/json` when body is a string and no Content-Type header is present
4. On HTTP 401 response: calls `authStore.logout()` and redirects to `/signin`

**Important**: Does NOT auto-set Content-Type for FormData (uploads) — the browser sets the multipart boundary automatically. This is handled by omitting Content-Type when body is not a string.

## Data & Control Flow

```
Component/Store → apiFetch(url, options)
                    ↓
              authStore.jwt → Authorization header
                    ↓
              native fetch(url, { ...options, headers })
                    ↓
              if 401 → logout() + router.push('/signin')
                    ↓
              return Response (unchanged)
```

## Integration Points

- **`authStore`**: Reads `jwt` for the auth header; calls `logout()` on 401
- **`router`**: Redirects to `/signin` on 401
- **All stores**: `jobStore`, `cvStore`, `authStore` (indirectly via components) all use `apiFetch` exclusively
- **Components**: `CoverLetterSection`, `RegeneratePanel`, `JobFormView`, `CvConverterView`, `SettingsView`, `BaseCvView`, `AppSidebar` all use `apiFetch` for direct API calls outside store actions
- **`SignInView`**: Uses raw `fetch` (not `apiFetch`) because the user is not yet authenticated; no JWT exists at sign-in time

## Functions

| Function | Signature | Purpose |
|---|---|---|
| `apiFetch` | `(input, init?) → Promise<Response>` | Authenticated fetch wrapper |
