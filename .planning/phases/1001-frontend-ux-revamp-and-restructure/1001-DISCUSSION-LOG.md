# Phase 1001: Frontend UX Revamp & Project Restructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 1001-frontend-ux-revamp-and-restructure
**Areas discussed:** Overall page layout & nav, Repo folder restructure, Component consistency

---

## Overall Page Layout & Nav

### Sidebar Direction

| Option | Description | Selected |
|--------|-------------|----------|
| Too cramped | Needs breathing room, better spacing, collapsible sections | |
| Navigation is buried | Import CV and Settings are tiny text links | |
| Whole layout needs rethinking | Maybe sidebar isn't the right pattern | |
| Keep sidebar, just redesign | Sidebar concept is fine but needs to be cleaner | ✓ |

**User's choice:** Keep sidebar, just redesign
**Notes:** User initially said "whole layout needs rethinking" for the sidebar question, then when asked about alternatives, chose to keep the sidebar but redesign it.

### Job Detail Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Too dense, needs sections | Needs clear section dividers or collapsible panels | |
| Wrong information hierarchy | Most important actions/content aren't prominent enough | |
| Both | Needs visual separation AND better ordering | |
| Tabs or accordion | Stop stacking everything — use tabs or collapsible panels | ✓ |

**User's choice:** Tabs or accordion

### Tab Grouping

| Option | Description | Selected |
|--------|-------------|----------|
| CV / Cover Letter / Analysis | Tab 1: CV preview + download. Tab 2: Cover letter. Tab 3: Gap analysis + tailoring notes | ✓ |
| Output / Analysis / Source | Tab 1: CV + cover letter. Tab 2: Gap + notes. Tab 3: Job listing | |
| All outputs together, source separate | Main view sections + collapsible job listing | |

**User's choice:** CV | Cover Letter | Analysis

---

## Repo Folder Restructure

### Core Logic Location

| Option | Description | Selected |
|--------|-------------|----------|
| Merge into backend/ | Move everything under backend/. One Python package. | |
| Flatten to src/ | Remove cv_maker/ nesting. src/pipeline.py etc. | |
| Rename to core/ | Replace src/cv_maker/ with core/ at top level | ✓ |

**User's choice:** Rename to core/

### Stray File Cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Delete all strays | Remove pipeline.py_new, output/, duplicate base_cv.yaml, sample PDF | ✓ |
| Gitignore output/, delete rest | Keep output/ but gitignore it | |
| I'll handle it manually | Don't touch stray files | |

**User's choice:** Delete all strays

---

## Component Consistency

### Selector Standardization

| Option | Description | Selected |
|--------|-------------|----------|
| Unify into shared pattern | Extract common pill/toggle base component or shared CSS class | ✓ |
| Visual consistency only | Keep separate but audit and align styles | |
| You decide | Claude's discretion | |

**User's choice:** Unify into shared pattern

### Button System

| Option | Description | Selected |
|--------|-------------|----------|
| Button hierarchy system | 3 levels: primary (blue), secondary (outline), danger (red) | ✓ |
| Contextual grouping | Group related actions visually by section | |
| Both | Button hierarchy AND contextual grouping | |

**User's choice:** Button hierarchy system (3 levels: primary, secondary, danger)

---

## Claude's Discretion

- Tab implementation approach
- Sidebar redesign specifics
- Shared component extraction strategy
- Job listing text placement within tabs

## Deferred Ideas

None
