# frontend/src/views/

## Responsibility

Top-level route-level Vue components. Each view corresponds to one route and composes sub-components to form a complete page. Views own page-level state (form inputs, loading flags, tab selection) and delegate business logic to Pinia stores.

## Design Patterns

- **Single-file components** with `<script setup lang="ts">`
- **Stores for data**: all server state flows through Pinia stores; views only hold transient UI state
- **`storeToRefs`**: used to destructure reactive store state while preserving reactivity
- **Route params as computed**: `JobDetailView` watches `route.params.id` to load/fetch on navigation
- **SSE lifecycle management**: `JobDetailView` opens SSE on mount when job is non-terminal, closes on unmount

---

## Views

### `JobFormView.vue` — Route `/`

**Purpose**: Landing page — submit a job description to generate a tailored CV.

**UI State**: `companyName`, `jobLink`, `jobText`, `submitting`, `errorMessage`, `selectedModel`, `selectedCreativity`

**Flow**:
1. On mount: fetches `/api/config` to determine which AI providers are available; auto-selects first available if default is unavailable
2. Form validation: both company name and job text must be non-empty
3. Submit: calls `store.submitJob(payload)` then `router.push('/jobs/' + id)`
4. Error: displays `ErrorBanner` with retry

**Integration**: Uses `ModelSelector`, `CreativitySlider`, `ErrorBanner`, `LoadingSpinner`. Reads provider availability from `/api/config`.

### `JobDetailView.vue` — Route `/jobs/:id`

**Purpose**: View and manage a job session with tabs for CV, Cover Letter, Analysis, and Job Listing.

**UI State**: `cancelling`, `downloading`, `deleting`, `regenerating`, `savingListing`, `isEditingCv`, `editableTailoredCv`, `savingCv`, `activeTab` (one of `'cv' | 'cover-letter' | 'analysis' | 'job-listing'`)

**Lifecycle**:
1. Watch `route.params.id`: on change, closes existing SSE, nulls `currentJob`, resets editing state, fetches new job, opens SSE if non-terminal
2. `onUnmounted`: closes SSE

**Tabs**:
- **CV**: Shows generating skeleton or CV preview; action buttons for download, edit CV, regenerate, delete; version history for previous CV generations. Toggling "Edit CV" switches to `<CvFormEditor>` to modify the tailored CV and recompile the PDF with version archiving.
- **Cover Letter**: Delegates entirely to `CoverLetterSection` component
- **Analysis**: Shows `GapDiffTable` and `TailoringNotes` if data exists
- **Job Listing**: Editable form for job link and description with save button

**Integration**: Uses `StatusBadge`, `ErrorBanner`, `LoadingSpinner`, `SkeletonSection`, `CvPreview`, `CvFormEditor`, `GapDiffTable`, `TailoringNotes`, `RegeneratePanel`, `CoverLetterSection`. All actions delegate to `jobStore`.

### `BaseCvView.vue` — Route `/base-cv`

**Purpose**: Edit the user's base CV (used as the starting point for tailoring).

**UI State**: `downloading`

**States**:
1. **Loading**: Spinner while fetching CV
2. **Empty** (no CV): Shows `PdfDropZone` + "Create CV from scratch" button
3. **Editing**: Uses shared `<CvFormEditor>` component with responsive 1040px scaling, auto-expanding textareas, drag-and-drop section reordering, and PDF download.

**Features**:
- Auto-expanding bullet textareas with zero internal scrolling
- Add/remove/reorder items within sections (↑↓ buttons)
- Save CV, Download PDF, Remove CV actions
- Re-upload zone at top even when CV exists

**Integration**: Uses `PdfDropZone`, `CvFormEditor`, `LoadingSpinner`. All data flows through `cvStore`.

### `CvConverterView.vue` — Route `/convert`

**Purpose**: Convert raw CV text (from .txt file or pasted) into structured YAML via AI.

**UI State**: `cvText`, `converting`, `successMessage`, `errorMessage`, `yamlContent`, `selectedModel`

**Flow**:
1. User uploads .txt file → FileReader populates textarea
2. Or user pastes text directly
3. Selects AI model via `ModelSelector`
4. Clicks "Convert to YAML" → POST `/api/cv/convert`
5. On success: shows success banner + rendered YAML preview; on error: error banner

**Integration**: Uses `ModelSelector`. Fetches `/api/config` for provider availability.

### `SettingsView.vue` — Route `/settings`

**Purpose**: Configure AI provider settings: model names, API keys, endpoints, cookie values.

**UI State**: `activeTab` (6 tabs), `settings` reactive object, `saving`, `saved`, `error`, `cookieChecking`, `cookieStatus`

**Tabs**:
- **General**: CV filename prefix for generated PDFs and per-user AI application-label rewriting toggle
- **Claude CLI**: Model name (uses local Claude Code subscription, no API key)
- **Claude API**: Model name + Anthropic API key
- **Gemini**: Model name + Google AI API key
- **OpenAI**: Model name, custom base URL (for OpenAI-compatible APIs), API key
- **Gemini Web**: Cookie (__Secure-1PSID), model name, "Test Connection" button

**Save behavior**: Masked API keys (starting with `***`) are omitted from the save payload so the backend doesn't overwrite stored keys with the masked string.

**Integration**: Uses `apiFetch` directly (no store). Loads settings from GET `/api/settings`, saves via PUT `/api/settings`. Cookie check via POST `/api/settings/check-gemini-web`.

### `SignInView.vue` — Route `/signin` (public)

**Purpose**: Google Sign-In page using Google Identity Services.

**Flow**:
1. On mount: fetches `/api/config` for `google_client_id`
2. Loads Google Identity Services on demand, waiting for SDK readiness before initialization. Already-loaded SDKs are reused; failed scripts are removed so retries can reload them; a 15-second script timeout prevents a stuck loading state.
3. Initializes with the client ID/callback and renders the Google sign-in button. Initialization/configuration failures show a retry button, without requiring a page refresh. Late completions do not render after the view unmounts.
4. On credential response: POSTs `id_token` to `/api/auth` (raw fetch, no JWT yet)
5. On success: `authStore.login(jwt, user)`, router push to `/`
6. On error: displays error message

**Integration**: Raw `fetch` for `/api/config` and `/api/auth` (pre-auth, no JWT). Uses `authStore.login`.
