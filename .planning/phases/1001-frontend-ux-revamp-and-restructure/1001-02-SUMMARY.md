---
phase: 1001-frontend-ux-revamp-and-restructure
plan: 02
subsystem: frontend
tags: [css, vue, design-system, button-hierarchy, sidebar]
dependency_graph:
  requires: []
  provides: [shared-selector-css, unified-pill-toggles, button-hierarchy, sidebar-redesign]
  affects: [ModelSelector, ToneSelector, CreativitySlider, RegeneratePanel, SessionEntry, AppSidebar]
tech_stack:
  added: []
  patterns: [shared-css-utility-classes, scoped-css-reduction]
key_files:
  created:
    - frontend/src/assets/selector.css
  modified:
    - frontend/src/components/ModelSelector.vue
    - frontend/src/components/ToneSelector.vue
    - frontend/src/components/CreativitySlider.vue
    - frontend/src/components/RegeneratePanel.vue
    - frontend/src/components/SessionEntry.vue
decisions:
  - "Extracted shared pill toggle CSS into selector.css (D-05) — all three selectors import this file; scoped CSS reduced to wrapper margin only"
  - "RegeneratePanel toggle demoted to Secondary (outline) per D-06; confirm button promoted to Primary (blue solid)"
  - "SessionEntry active state uses left-border indicator (3px solid #2563eb) replacing blue background — aligns with sidebar contract"
  - "AppSidebar.vue was already spec-compliant — no changes required"
metrics:
  duration: 131s
  completed: 2026-04-07
  tasks_completed: 2
  files_modified: 6
---

# Phase 1001 Plan 02: CSS Unification, Button Hierarchy, Sidebar Redesign Summary

Extracted shared pill-toggle CSS into `selector.css`, unified all three selectors to identical CSS classes, fixed RegeneratePanel button hierarchy from amber to Secondary/Primary, and redesigned SessionEntry to use a left-border active indicator with proper spacing.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create shared selector.css and unify ModelSelector, ToneSelector, CreativitySlider | afca450 | frontend/src/assets/selector.css, ModelSelector.vue, ToneSelector.vue, CreativitySlider.vue |
| 2 | Fix button hierarchy in RegeneratePanel and redesign SessionEntry | e4d04c2 | RegeneratePanel.vue, SessionEntry.vue |

## What Was Built

### selector.css (new)

A shared CSS utility file (`frontend/src/assets/selector.css`) containing `.pill-group`, `.pill-option`, `.pill-option--active`, `.pill-option--disabled`, `.field-label`, `.field-hint`, and `.field-hint--warning`. All three selector components now import this file instead of duplicating 50+ lines of identical CSS each.

### Unified Pill Toggles

ModelSelector, ToneSelector, and CreativitySlider each had component-specific class names (`.model-toggle`, `.tone-toggle`, `.creativity-toggle`, etc.). All are now replaced with shared `.pill-group`/`.pill-option` classes. Scoped `<style>` blocks in each component reduced to a single wrapper margin rule.

### Button Hierarchy Fix (D-06)

RegeneratePanel's amber (#f59e0b) buttons fully replaced:
- Toggle "Regenerate": Secondary outline style — transparent bg, `border: 1px solid #e2e8f0`, `color: #374151`, hover darkens border/text
- Confirm "Regenerate Now": Primary blue solid — `background: #2563eb`, hover `#1d4ed8`

### SessionEntry Redesign (D-01 Sidebar Contract)

- Padding: `8px 16px` → `12px 16px`
- Removed `border-bottom: 1px solid #e2e8f0` (individual entry borders not in spec)
- Color: `#374151` → `#111827`
- Hover: `#f1f5f9` → `#f9fafb`
- Active state: replaced blue background (`#eff6ff`) + blue text (`#1e40af`) with gray background (`#f3f4f6`) + `border-left: 3px solid #2563eb`

### AppSidebar.vue

Already spec-compliant — no changes required.

## Decisions Made

1. **Shared CSS import over base component abstraction**: Per D-05 recommendation, extracted CSS utility classes into `selector.css` rather than creating a new Vue base component. This avoids changing prop contracts and is simpler to reason about. Each selector imports the file in `<script setup>`.

2. **Left-border active indicator over background highlight**: The sidebar contract specifies `background: #f3f4f6` + `border-left: 3px solid #2563eb` for the active SessionEntry. This is visually cleaner than the previous full blue background and matches the standard sidebar pattern.

3. **AppSidebar left as-is**: After reading AppSidebar.vue against the UI spec, all CSS values already matched the spec contract (header padding, header-links flex row, cv-info border-top, margin-top auto). No changes made.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all components wire to real data. No placeholder or hardcoded empty values introduced.

## Self-Check: PASSED

- `frontend/src/assets/selector.css` exists and contains `.pill-group {`
- Commits `afca450` and `e4d04c2` exist
- TypeScript compilation: zero errors
- Amber color `#f59e0b` fully removed from RegeneratePanel.vue
- `border-left: 3px solid #2563eb` present in SessionEntry.vue
