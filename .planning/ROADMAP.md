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
**Requirements**: TBD
**Depends on:** Current codebase (no phase dependency)
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 1000 to break down)
