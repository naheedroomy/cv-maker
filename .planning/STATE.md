---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Deploy, Auth & CV Editor
status: executing
stopped_at: Completed 1005-01-PLAN.md
last_updated: "2026-04-07T17:35:54.649Z"
last_activity: 2026-04-07
progress:
  total_phases: 8
  completed_phases: 5
  total_plans: 17
  completed_plans: 16
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-05)

**Core value:** Given a job listing and a base CV, produce a tailored CV that honestly highlights the most relevant experience and skills — never fabricate, only emphasize and reframe.
**Current focus:** Phase 1005 — dockerization-and-docker-compose

## Current Position

Phase: 1005 (dockerization-and-docker-compose) — EXECUTING
Plan: 2 of 2
Status: Ready to execute
Last activity: 2026-04-07

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

| Phase 05 P01 | 174s | 3 tasks | 8 files |
| Phase 05 P02 | 90s | 2 tasks | 5 files |
| Phase 07 P02 | 420s | 2 tasks | 6 files |
| Phase 09 P01 | 480s | 2 tasks | 8 files |
| Phase 09 P02 | 189s | 2 tasks | 7 files |
| Phase 09 P03 | 300s | 2 tasks | 3 files |
| Phase 09 P03 | 15s | 3 tasks | 3 files |
| Phase 09 P04 | 180s | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Archived to PROJECT.md Key Decisions table.

- [Phase 1000]: ToneSelector clones ModelSelector.vue pill pattern per D-04, replacing .model- prefix with .tone- and removing availability check complexity
- [Phase 1000]: CoverLetterSection uses storeToRefs for reactive currentJob to resolve company name for PDF download filename without extra prop
- [Phase 1000]: Standalone generate_cover_letter() function rather than ABC method — different signature avoids forcing all 4 providers to implement a second method
- [Phase 1000]: fpdf2 for cover letter PDF — pure Python, zero system deps, vs LaTeX (overkill) or WeasyPrint (C libs)
- [Phase 1000]: CoverLetterSaveRequest defined locally in cover_letter.py router — not shared across routers, avoids cluttering schemas.py
- [Phase 1001]: Shared selector.css (not base component) for pill-toggle unification per D-05 — avoids prop contract changes, simpler to reason about
- [Phase 1001]: SessionEntry active state uses left-border indicator (3px solid #2563eb) over blue background — cleaner, aligns with sidebar contract
- [Phase 1001]: Use git mv src/cv_maker core to preserve git history for all moved files
- [Phase 1001]: Add [tool.hatch.build.targets.wheel] packages = ['core'] so hatchling finds the package at repo root (not under src/)
- [Phase 1001]: Tab panels use v-show (not v-if) for instant switching — preserves CoverLetterSection form state across tab switches
- [Phase 1001]: Cancel Job moved outside tabs to running-actions area — tabs only shown when job is complete/failed/cancelled
- [Phase quick]: get_api_key() centralizes DB-overrides-.env logic for all 3 API providers
- [Phase 1002]: Eliminated in-process settings cache - get_setting and get_api_key are now async with per-user DB lookups — Per-user settings require direct DB queries - in-process cache was incompatible with multi-tenant model
- [Phase 1002]: Provider constructors accept explicit params (api_key, model) — settings resolution moved to async get_provider() factory, decoupling core/ providers from backend/ settings_cache
- [Phase 1003]: Dynamic import of useAuthStore inside beforeEach guard avoids circular dependency between router and store at module load time
- [Phase 1003]: window.location.href for 401 redirect instead of router.push — ensures full page reload and state reset
- [Phase 1003]: apiFetch pattern: auto-Bearer + 401 redirect; plain fetch for pre-auth calls (/api/config, /api/auth/google) to avoid redirect loops
- [Phase 1003]: asyncio_mode=auto in pytest config removes need for @pytest.mark.asyncio decorator on every async test
- [Phase 1003]: CORS_ORIGINS env var with comma-split supports multiple origins for staging+production without code changes
- [Phase 1003]: config endpoint stays public (no get_current_user) — feature flags and google_client_id needed before auth is established
- [Phase 1003]: apiFetch drop-in replaces all native fetch() in jobStore — Bearer token auto-injected, 401 triggers logout+redirect
- [Phase 1003]: AppSidebar user profile uses authStore storeToRefs — reactive display of Google avatar, name, sign-out without props
- [Phase 1004]: Gemini 2.5 Flash-Lite for both OCR and structuring passes in CV parser; inhouse GEMINI_API_KEY from .env; DB CV takes priority over YAML file in GET /cv/info
- [Phase 1004]: user_id defaults to 1 (ANONYMOUS_USER_ID) in job_worker for backward compat — DB-first CV load with YAML fallback
- [Phase 1004]: Sidebar fetchCvInfo uses apiFetch (not plain fetch) to carry JWT Bearer token for /api/cv/me
- [Phase 1004]: Optional chaining + explicit index guard for TypeScript array access: const item = arr?.[i]; if (!item) return — satisfies strict type checker without noUncheckedIndexedAccess
- [Phase 1004]: v-show for CvEditorSection collapse (not v-if) — preserves form input state when re-expanding collapsed sections
- [Phase 1005]: Split backend/frontend into separate containers — backend has no frontend code, SPA served by Nginx; npm ci for reproducible builds

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260405-4j5 | Fix stale CLAUDE.md recommended stack section | 2026-04-04 | d49d4bd | [260405-4j5-fix-stale-claude-md-recommended-stack-se](./quick/260405-4j5-fix-stale-claude-md-recommended-stack-se/) |
| 260405-o4h | Fix v2.0 milestone tech debt: SSE payload, dead export, REQUIREMENTS.md | 2026-04-05 | 0d20b72 | [260405-o4h-fix-v2-0-milestone-tech-debt](./quick/260405-o4h-fix-v2-0-milestone-tech-debt/) |
| 260405-q36 | Update CLAUDE.md and PROJECT.md to reflect Gemini 3.1 Flash-Lite and python-dotenv | 2026-04-05 | 0e94ea3 | [260405-q36-update-claude-md-and-project-md-to-refle](./quick/260405-q36-update-claude-md-and-project-md-to-refle/) |
| 260405-srf | Add OpenAI-compatible API provider as third model option | 2026-04-05 | f64b28c | [260405-srf-add-openai-compatible-api-provider-as-th](./quick/260405-srf-add-openai-compatible-api-provider-as-th/) |
| 260406-jb6 | Add creativity slider (0-5) to control AI tailoring liberty | 2026-04-06 | faad203 | [260406-jb6-add-creativity-slider-to-control-ai-tail](./quick/260406-jb6-add-creativity-slider-to-control-ai-tail/) |
| 260406-k1w | Redesign regenerate UI with model and creativity controls | 2026-04-06 | 1e7355e | [260406-k1w-redesign-regenerate-ui-with-model-and-cr](./quick/260406-k1w-redesign-regenerate-ui-with-model-and-cr/) |
| 260407-hg6 | Add Core Competencies pills, bullet reordering, anti-pruning | 2026-04-07 | 3d451c2 | [260407-hg6-add-core-competencies-pills-bullet-reord](./quick/260407-hg6-add-core-competencies-pills-bullet-reord/) |
| 260407-qcs | API key management in Settings + Job Listing tab in JobDetailView | 2026-04-07 | 442bb5d | [260407-qcs-api-key-management-in-settings-enable-di](./quick/260407-qcs-api-key-management-in-settings-enable-di/) |
| Phase 1000 P02 | 2min | 2 tasks | 4 files |
| Phase 1000 P01 | 162 | 2 tasks | 6 files |
| Phase 1000 P03 | 8min | 2 tasks | 4 files |
| Phase 1001 P02 | 131s | 2 tasks | 6 files |
| Phase 1001 P01 | 720 | 2 tasks | 26 files |
| Phase 1001 P03 | 167 | 1 tasks | 2 files |
| Phase 1002 P01 | 1min | 1 tasks | 1 files |
| Phase 1002 P02 | 1min | 1 tasks | 1 files |
| Phase 1002 P03 | 3min | 7 tasks | 11 files |
| Phase 1003 P02 | 2 | 2 tasks | 5 files |
| Phase 1003 P01 | 230 | 2 tasks | 7 files |
| Phase 1003 P03 | 15min | 2 tasks | 7 files |
| Phase 1004 P01 | 216 | 2 tasks | 8 files |
| Phase 1004 P03 | 166 | 2 tasks | 3 files |
| Phase 1004 P02 | 564 | 2 tasks | 5 files |
| Phase 1005 P01 | 94s | 3 tasks | 3 files |

### Roadmap Evolution

- Phase 999.1 added (backlog): Visual template selector in Settings
- Phase 1000 added: Cover Letter Generator

## Session Continuity

Last session: 2026-04-07T17:35:54.645Z
Stopped at: Completed 1005-01-PLAN.md
Resume file: None
