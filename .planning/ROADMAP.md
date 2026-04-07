# Roadmap: CV Maker

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-04-04) — [archive](milestones/)
- ✅ **v2.0 Full-Stack Rebuild** — Phases 5-9 (shipped 2026-04-05) — [archive](milestones/v2.0-ROADMAP.md)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-04-04</summary>

- [x] Phase 1: Data Foundation (1/1 plans) — completed 2026-04-03
- [x] Phase 2: LaTeX Renderer (2/2 plans) — completed 2026-04-04
- [x] Phase 3: AI Pipeline (3/3 plans) — completed 2026-04-04
- [x] Phase 4: Streamlit UI (2/2 plans) — completed 2026-04-04

</details>

<details>
<summary>✅ v2.0 Full-Stack Rebuild (Phases 5-9) — SHIPPED 2026-04-05</summary>

- [x] Phase 5: Backend Foundation (2/2 plans) — completed 2026-04-04
- [x] Phase 6: Job Queue & API (3/3 plans) — completed 2026-04-04
- [x] Phase 7: Vue Frontend (3/3 plans) — completed 2026-04-04
- [x] Phase 8: Production Wiring (2/2 plans) — completed 2026-04-04
- [x] Phase 9: Gemini Provider (4/4 plans) — completed 2026-04-05

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 1/1 | Complete | 2026-04-03 |
| 2. LaTeX Renderer | v1.0 | 2/2 | Complete | 2026-04-04 |
| 3. AI Pipeline | v1.0 | 3/3 | Complete | 2026-04-04 |
| 4. Streamlit UI | v1.0 | 2/2 | Complete | 2026-04-04 |
| 5. Backend Foundation | v2.0 | 2/2 | Complete | 2026-04-04 |
| 6. Job Queue & API | v2.0 | 3/3 | Complete | 2026-04-04 |
| 7. Vue Frontend | v2.0 | 3/3 | Complete | 2026-04-04 |
| 8. Production Wiring | v2.0 | 2/2 | Complete | 2026-04-04 |
| 9. Gemini Provider | v2.0 | 4/4 | Complete | 2026-04-05 |

## Backlog

### Phase 999.1: Visual template selector in Settings (BACKLOG)

**Goal:** Let users choose from multiple LaTeX CV templates via a visual gallery in the Settings panel. Each template shows a thumbnail preview; the selected template is used for all PDF renders.
**Scope:** Multiple .tex.jinja templates, template metadata (name, preview image), settings DB field, renderer template selection, frontend preview gallery component.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 1000: Cover Letter Generator

**Goal:** Users can generate a tailored cover letter alongside their tailored CV — using the base CV, job listing, and tailored CV output as inputs. Cover letters sound human (no AI-smell) via humanizer-inspired anti-pattern rules and a two-pass generate-then-self-critique architecture.
**Scope:**
- User notes field: free-text bullet points the user wants woven into the cover letter (e.g., "mention I'm relocating to Berlin", "highlight my K8s migration project")
- New cover letter prompt with anti-AI-smell rules (no significance inflation, no promotional language, simple verbs, varied rhythm, specificity over scope, no generic conclusions)
- Two-pass architecture: generate draft → self-critique for AI tells → revise
- Reuse existing provider abstraction (all 4 providers)
- New Pydantic model for cover letter output
- New API endpoint (POST /api/jobs/:id/cover-letter or integrated into job pipeline)
- Vue component for cover letter preview + download with editable notes input
- Optional: PDF rendering via LaTeX or plain text output
- Creativity slider applies to cover letter tone/boldness
**Branch:** `feature/cover-letter` (not master direct)
**Requirements**: CL-CORE, CL-PROMPT, CL-PDF, CL-DB, CL-TONE, CL-UI, CL-NOTES, CL-EDIT, CL-API, CL-WIRE, CL-BRANCH
**Depends on:** Current codebase (no phase dependency)
**Plans:** 3/3 plans complete

Plans:
- [x] 1000-01-PLAN.md — Backend core: cover letter generation module, fpdf2 renderer, DB migration, API schemas
- [x] 1000-02-PLAN.md — Frontend: ToneSelector, CoverLetterSection components, types, store actions
- [x] 1000-03-PLAN.md — Integration: API router, main.py wiring, JobDetailView integration, end-to-end verification

### Phase 1001: Frontend UX Revamp & Project Restructure

**Goal:** Revamp the frontend UX for a cleaner, less clunky experience — 3-tab layout for job detail, unified pill selectors, 3-level button hierarchy, sidebar facelift. Restructure the repo folder layout to flatten src/cv_maker/ into core/ and delete stray files.
**Scope:**
- Frontend UX cleanup: 3-tab job detail layout (CV / Cover Letter / Analysis), button hierarchy, selector unification
- Cover letter section promoted to its own tab for discoverability
- Regenerate panel button style corrections (Secondary toggle, Primary confirm)
- Sidebar facelift: active left-border indicator, proper session entry spacing
- Project folder restructure: rename src/cv_maker/ to core/, update all imports, delete stray files
**Requirements**: REPO-RENAME, REPO-CLEANUP, UX-SELECTORS, UX-BUTTONS, UX-SIDEBAR, UX-TABS
**Depends on:** Phase 1000
**Plans:** 1/3 plans executed

Plans:
- [ ] 1001-01-PLAN.md — Repo restructure: rename src/cv_maker/ to core/, update imports, delete stray files
- [x] 1001-02-PLAN.md — Shared selector CSS, button hierarchy fixes, sidebar redesign
- [ ] 1001-03-PLAN.md — 3-tab layout in JobDetailView, CoverLetterSection tab adaptation, visual checkpoint
