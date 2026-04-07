# Phase 1001: Frontend UX Revamp & Project Restructure - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Two workstreams: (1) revamp the frontend UX for a cleaner, less clunky experience with proper visual hierarchy and tabbed content organization, and (2) restructure the repo folder layout to flatten the confusing src/cv_maker/ nesting and clean up stray files.

</domain>

<decisions>
## Implementation Decisions

### Overall Page Layout & Navigation
- **D-01:** Keep the sidebar but redesign it — cleaner styling, better spacing, proper nav items instead of tiny text links. The sidebar concept is fine but needs a facelift.
- **D-02:** Job detail page switches from vertical stacking to 3 tabs: **CV** (tailored CV preview + download), **Cover Letter** (generate/edit/download), **Analysis** (gap analysis + tailoring notes). Job listing text goes in a collapsible section or the Analysis tab.

### Repo Folder Restructure
- **D-03:** Rename `src/cv_maker/` to `core/` at the top level. The module becomes `core/pipeline.py`, `core/models.py`, `core/providers/`, `core/cover_letter.py`, `core/renderer.py`, etc. All imports across `backend/` update accordingly.
- **D-04:** Delete all stray files: `pipeline.py_new`, `output/`, duplicate `base_cv.yaml` at root, `001-helsing-sre.pdf`. Keep `data/base_cv.yaml` as the single source.

### Component Consistency
- **D-05:** Unify ModelSelector, ToneSelector, and CreativitySlider into a shared pill/toggle base component or shared CSS class. All selectors must look and behave identically: same button height, padding, active color, hint text position, disabled state.
- **D-06:** Implement a 3-level button hierarchy system applied consistently everywhere:
  - **Primary** (blue solid) — key actions: Download PDF, Generate Cover Letter, Save & Download
  - **Secondary** (outline) — supporting actions: Copy, Regenerate, Cancel
  - **Danger** (red) — destructive: Delete Job

### Claude's Discretion
- Tab implementation approach (native Vue tabs vs component library)
- Sidebar redesign specifics (icon choice, collapsible behavior, width)
- Shared component extraction strategy (base component vs CSS utility classes)
- How to handle the job listing text (4th tab vs collapsible within Analysis tab)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

### Existing Components to Audit
- `frontend/src/components/ModelSelector.vue` — current pill selector pattern (to be unified)
- `frontend/src/components/ToneSelector.vue` — similar pill pattern (to be unified)
- `frontend/src/components/CreativitySlider.vue` — slider variant (to be unified)
- `frontend/src/components/RegeneratePanel.vue` — regenerate UX (to be improved)
- `frontend/src/components/CoverLetterSection.vue` — cover letter UI (moves to its own tab)
- `frontend/src/components/AppSidebar.vue` — sidebar (to be redesigned)
- `frontend/src/views/JobDetailView.vue` — main detail page (to be tabbed)

### Core Module to Restructure
- `src/cv_maker/` — entire directory moves to `core/`
- `backend/` — all imports referencing `cv_maker.*` must update to `core.*`
- `pyproject.toml` — package configuration must update for new module path

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ModelSelector.vue`: Pill toggle with v-model, disabled states, availability checks, hint text — closest to a "base" selector pattern
- `StatusBadge.vue`: Simple status display — can stay as-is
- `LoadingSpinner.vue`: Already reused across components — no changes needed

### Established Patterns
- All components use scoped CSS with consistent color tokens (#2563eb blue, #e2e8f0 border, #111827 text)
- Pinia store with `storeToRefs` for reactive state — well established
- Components use `defineProps`/`defineEmits` with TypeScript generics

### Integration Points
- `JobDetailView.vue` is the main orchestrator — will need the most rework for tabs
- `AppSidebar.vue` connects via Vue Router — redesign must preserve routing
- `pyproject.toml` `[tool.setuptools.packages.find]` must update for `core/` rename
- All `from cv_maker.` imports in `backend/` must change to `from core.`

</code_context>

<specifics>
## Specific Ideas

- User explicitly called out the regenerate button, cover letter discoverability, and small buttons as pain points
- The `src/cv_maker/` nesting was called out as confusing — "isn't src/ just enough?"
- User wants it "clean" — implies minimal, well-spaced, clear hierarchy

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 1001-frontend-ux-revamp-and-restructure*
*Context gathered: 2026-04-07*
