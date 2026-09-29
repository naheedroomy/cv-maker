# frontend/src/components/

## Responsibility

Reusable Vue components that compose into views. Each component has a single, focused responsibility. Components communicate via props (down) and emits (up); they access stores directly for global state.

## Design Patterns

- **Props-driven rendering**: components receive data via typed `defineProps<{}>()`  
- **Event-based communication**: `defineEmits<{}>()` for parent callbacks
- **Store access**: some components access Pinia stores directly (`AppSidebar`, `CoverLetterSection`) for shared state
- **Scoped styles**: all components use `<style scoped>` to prevent CSS leakage
- **Shared CSS**: `ModelSelector` and `CreativitySlider` import `@/assets/selector.css` for consistent pill-group styling

---

## Components

### `AppSidebar.vue`
**Purpose**: Left sidebar shell — job search, session list, CV info, user profile, navigation.

**Data & State**:
- Reads `jobs` from `jobStore` via `storeToRefs`, polls every 30s via `setInterval`
- Reads `user` and `isAuthenticated` from `authStore`
- Local `searchQuery` (reactive) filters jobs by company name
- Local `cvInfo` (fetched from `/api/cv/me`) shows base CV status

**Key behaviors**:
- `sortedJobs`: computed, filters by search and sorts newest-first
- `fetchCvInfo()`: called on mount in parallel with `fetchJobs()`
- Sign-out: `authStore.logout()` + `router.push('/signin')`

**Integration**: Imports `SessionEntry`, uses `RouterLink`, calls `apiFetch` directly. Exposes CSS class `sidebar--open` for mobile toggle controlled by `App.vue`.

### `SessionEntry.vue`
**Purpose**: Single job session row in the sidebar.

**Props**: `job: JobResponse`, `active: boolean`

**Rendering**: Company name, "Applied" badge, formatted date, CV/CL status indicators (colored labels). Active state shows blue left border. Uses `<router-link>` for navigation.

**Status indicators**: CV state (done/pending/failed) shown via colored `CV` label; Cover Letter state shown via `CL` label.

### `StatusBadge.vue`
**Purpose**: Colored badge for job status values.

**Props**: `status: JobStatus`

**States**: `pending`/`running` → yellow, `complete` → green, `failed` → red, `cancelled` → gray. ARIA label includes status text.

### `ErrorBanner.vue`
**Purpose**: Dismissable error banner with retry button.

**Props**: `message: string`  
**Emits**: `retry`

**Rendering**: Red left border, error text, blue "Try again" link button.

### `LoadingSpinner.vue`
**Purpose**: Pure CSS loading spinner (24×24px, blue top border, 0.7s rotation). No props, no state — purely presentational. `role="status"`, `aria-label="Loading"`.

### `SkeletonSection.vue`
**Purpose**: Placeholder loading animation for CV generation.

**Props**: `title: string`, `lines?: number` (default 3)

**Rendering**: Section with title, "Generating..." label, animated pulse bars (last bar at 60% width for visual variety).

### `ModelSelector.vue`
**Purpose**: Pill-group selector for AI model choice across all providers.

**Props**: `modelValue: string`, `claudeApiAvailable`, `geminiAvailable`, `openaiAvailable`, `geminiWebAvailable`, `disabled: boolean`  
**Emits**: `update:modelValue`

**Options**: Claude API, Gemini, OpenAI, Gemini Web — each with description hints. Unavailable options are visually disabled and show "Set your X in Settings" hint. Selected option shows its provider hint text.

**Integration**: Imports `@/assets/selector.css` for shared pill styles. Used by `JobFormView`, `RegeneratePanel`, `CoverLetterSection`, `CvConverterView`.

### `CreativitySlider.vue`
**Purpose**: Pill-group selector for creativity level (0–3).

**Props**: `modelValue: number`, `disabled: boolean`  
**Emits**: `update:modelValue`

**Levels**: 0 (Strict) through 3 (Selective). Each level has a descriptive hint.

**Integration**: Imports `@/assets/selector.css`. Used by `JobFormView` and `RegeneratePanel`.

### `RegeneratePanel.vue`
**Purpose**: Expandable panel for CV regeneration with model overrides, reasoning effort, creativity level, and custom instructions.

**Props**: `currentModel: string`, `currentCreativityLevel: number`, `currentNotes?: string | null`, `currentModelId?: string | null`, `currentReasoningEffort?: string | null`, `disabled: boolean`  
**Emits**: `regenerate(model, creativityLevel, userNotes, modelId?, reasoningEffort?)`

**Behavior**:
- Toggle button shows "Regenerate" or "Cancel" (when expanded) or "Regenerating..." (when disabled)
- Expanded panel: `ModelSelector` (with model override & reasoning effort details) + `CreativitySlider` (0–3) + Custom instructions textarea + "Regenerate Now" button
- Provider availability fetched from `/api/config` on mount
- Selections reset to current job props when props change (job navigation)

### `PdfDropZone.vue`
**Purpose**: Drag-and-drop PDF upload zone with click-to-browse fallback.

**Props**: `uploading: boolean`, `uploadProgress: string`  
**Emits**: `upload(file: File)`

**States**:
- **Idle**: Upload icon + "Drop your CV (PDF) here or click to browse" + "PDF files only"
- **Dragover**: Blue border highlight
- **Uploading**: `LoadingSpinner` + progress text, click disabled

**Validation**: Rejects non-PDF files with `alert()`. Resets file input value so same file can be re-uploaded. Keyboard accessible (Enter/Space to open picker).

### `CvEditorSection.vue`
**Purpose**: Collapsible content section with header toggle — used as building block for the CV editor.

**Props**: `title: string`, `collapsed?: boolean`, `draggableHint?: boolean`  
**Emits**: `toggle`  
**Slot**: Default slot for section body content

**Rendering**: Header bar with drag handle (☰ icon, shown when `draggableHint` is true), title, chevron (rotates -90° when collapsed). Body shown/hidden via `v-show`. Background highlight on header hover.

### `CvFormEditor.vue`
**Purpose**: Shared, responsive CV editor with auto-expanding textareas and scalable cards. Used by `BaseCvView` and `JobDetailView`.

**Props**: `modelValue: BaseCV | TailoredCV`, `title?: string`, `saveLabel?: string`, `saving?: boolean`, `showCancel?: boolean`, `showDownload?: boolean`, `downloading?: boolean`  
**Emits**: `update:modelValue`, `save`, `cancel`, `download`

**Features**:
- Auto-growing textareas for achievement bullets, summary, and project descriptions (`field-sizing: content` + `v-auto-grow` directive) with zero internal scrolling.
- Responsive grid and card layout up to 1040px with reorderable sections, entry move up/down, add/remove items.
- Works seamlessly for both base CVs and tailored CVs.

### `CvPreview.vue`
**Purpose**: Renders a `TailoredCV` object as formatted sections.

**Props**: `cv: TailoredCV`

**Sections rendered** (conditionally based on data presence):
- Summary (text)
- Experience (company, title, date range, bullets)
- Certifications (bullet list)
- Education (institution, degree, field, year)
- Skills (comma-separated)
- Highlighted Technologies (comma-separated)
- Projects (name, URL link, description, technologies)

### `GapDiffTable.vue`
**Purpose**: Table displaying gap analysis results.

**Props**: `items: GapItem[]`

**Columns**: Requirement (with optional evidence subtext), Status (Strong/Partial/Gap badge). Color-coded: green for strong match, yellow for partial, red for gap.

### `TailoringNotes.vue`
**Purpose**: Table showing AI tailoring notes — explains what the AI changed and why.

**Props**: `notes: TailoringNote[]`

**Columns**: Section, Action (Modified/Added/Removed/Reordered/Unchanged — color-coded badges), Change, Reason. Header has amber background to distinguish from gap analysis.

### `CoverLetterSection.vue`
**Purpose**: Full cover letter lifecycle component — generate, preview, edit, copy, save/download, version history.

**Props**: `jobId`, `jobStatus`, `currentModel`, `existingCoverLetter`, `existingNotes`, `existingClModel`, `existingClTone`, `clHistory`  
**Store access**: Uses `jobStore` via `storeToRefs` for `currentJob`

**States**:
1. **No cover letter** (no text, no form open): "Generate Cover Letter" button (disabled if CV not complete)
2. **Form open** (showForm=true): ModelSelector with model variant and reasoning effort details + optional custom instructions textarea + Generate button
3. **Generating**: LoadingSpinner + text
4. **Generated**: Editable textarea + Copy/Save&Download/Regenerate buttons + metadata badges
5. **Version history**: Always shown at top if `clHistory` exists — allows loading past versions

**Key behaviors**:
- Background generation detection: if `existingCoverLetter === ''` on mount, shows generating state; watcher detects when text arrives
- `handleGenerate`: POSTs via store, polls for completion, updates local text
- `handleCopy`: clipboard API with 2s "Copied!" feedback
- `handleSaveAndDownload`: PUT save then GET PDF download
- Provider availability: fetched from `/api/config` on mount

**Integration**: Uses `ModelSelector` (`:show-model-details="true"` for model and reasoning effort selection), `LoadingSpinner`. All API calls through `jobStore` actions.
