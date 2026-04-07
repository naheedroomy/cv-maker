---
phase: 1001-frontend-ux-revamp-and-restructure
plan: 03
subsystem: frontend
tags: [vue, tab-layout, ux, button-hierarchy, cover-letter]
dependency_graph:
  requires: [1001-02]
  provides: [tab-layout, cover-letter-tab, analysis-tab]
  affects: [JobDetailView, CoverLetterSection]
tech_stack:
  added: []
  patterns: [tab-navigation, v-show-instant-swap, button-hierarchy]
key_files:
  created: []
  modified:
    - frontend/src/views/JobDetailView.vue
    - frontend/src/components/CoverLetterSection.vue
decisions:
  - "Tab panels use v-show (not v-if) for instant switching with no animation per UI spec"
  - "Tab bar renders only when status is complete/failed/cancelled — loading state occupies full content area"
  - "Cancel Job button moved to running-actions area below spinner (outside tabs) per plan spec"
  - "CoverLetterSection outer v-if guard removed — parent tab only mounts it when status is complete"
metrics:
  duration: 167s
  completed: 2026-04-07
  tasks_completed: 1
  files_modified: 2
---

# Phase 1001 Plan 03: 3-Tab Layout for JobDetailView Summary

Restructured JobDetailView from vertical stacking to a 3-tab layout (CV / Cover Letter / Analysis) using instant v-show switching; adapted CoverLetterSection for tab context with Primary generate button.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add 3-tab layout to JobDetailView and adapt CoverLetterSection | eb704ca | frontend/src/views/JobDetailView.vue, frontend/src/components/CoverLetterSection.vue |

## Task 2: Checkpoint Pending

**Type:** checkpoint:human-verify (blocking)
**Status:** Awaiting human visual verification

Task 2 is a visual verification checkpoint. The human needs to run the dev servers and confirm:
- 3-tab layout renders correctly (CV / Cover Letter / Analysis)
- Tab switching is instant (no animation)
- CV tab default on load and resets on job navigation
- Cover Letter tab shows Primary blue "Generate Cover Letter" button
- Analysis tab shows gap analysis, tailoring notes, job listing
- All buttons follow 3-level hierarchy (Primary blue, Secondary outline, Danger red/gray)
- Sidebar and selector improvements from Plan 02 also verified at this checkpoint

See `1001-03-PLAN.md` Task 2 `<how-to-verify>` section for complete checklist.

## What Was Built

### JobDetailView.vue restructured into 4 zones

**Zone 1 — HEADER:** Company heading + StatusBadge + model badges + applied toggle + job link. Always visible. No changes to existing header content.

**Zone 2 — LOADING/RUNNING STATE:** Spinner with status text, SkeletonSection components (when running), and Cancel Job button (Secondary outline style). Shown only when status is pending/running.

**Zone 3 — TAB BAR:** Three tab buttons (CV / Cover Letter / Analysis) with 44px height, border-bottom active indicator in accent blue (`#2563eb`). Shown only when status is complete/failed/cancelled.

**Zone 4 — TAB PANELS:** Three `v-show`-controlled panels for instant switching.
- CV tab: Download PDF (Primary), RegeneratePanel (already redesigned in Plan 02), Delete (Danger), CvPreview
- Cover Letter tab: CoverLetterSection component + empty state text for non-complete jobs
- Analysis tab: GapDiffTable, TailoringNotes, job listing text, empty state

### CoverLetterSection.vue adapted for tab context

- Removed `<h3 class="section-heading">Cover Letter</h3>` — tab label provides context
- Removed `margin-top: 32px` from `.cover-letter-section` — tab panel handles spacing
- Promoted `.btn-generate-trigger` from Secondary outline to Primary blue (`background: #2563eb`)
- Removed outer `v-if="jobStatus === 'complete'"` guard — parent tab handles this condition

### Button hierarchy fully implemented

| Button | Class | Style |
|--------|-------|-------|
| Download PDF | `.btn-primary` | Blue solid #2563eb |
| Cancel Job | `.btn-secondary` | Outline #e2e8f0 border |
| Delete | `.btn-danger` | Gray outline, red on hover |

Old classes `.btn-download`, `.btn-cancel`, `.btn-delete` fully removed.

## Decisions Made

1. **v-show over v-if for tab panels**: Per UI spec — "instant swap, no animation." v-show keeps all tab panel DOM alive and switches visibility instantly. v-if would destroy/recreate the CoverLetterSection on every tab switch (losing form state).

2. **Tab bar condition guards on v-show panels**: Rather than wrapping all panels in a single `v-if="['complete', 'failed', 'cancelled'].includes(..."`, the condition is also encoded in each `v-show` expression to ensure panels are never visible during loading state.

3. **Cancel Job outside tabs**: The Cancel Job button lives in a `.running-actions` area below the spinner/skeletons — this is only visible during pending/running, which is mutually exclusive with the tab bar. This avoids having a tab with a single button as its only content.

4. **CoverLetterSection v-if guard removal**: The parent CV tab already guards with `v-if="currentJob.status === 'complete'"` before rendering CoverLetterSection. The redundant inner guard was removed, simplifying the component.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all components wire to real data. No placeholder or hardcoded empty values introduced.

## Self-Check: PASSED

- `frontend/src/views/JobDetailView.vue` modified — contains `activeTab`, `tab-bar`, 3 `tab-btn` instances
- `frontend/src/components/CoverLetterSection.vue` modified — no heading, no margin-top 32px, Primary generate button
- Commit `eb704ca` exists
- Old classes `btn-download`, `btn-cancel`, `btn-delete` fully absent from JobDetailView.vue
- TypeScript compilation: zero errors (`npx vue-tsc --noEmit` — no output)
- Task 2 (human-verify checkpoint) is pending — documented above
