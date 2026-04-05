---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Full-Stack Rebuild
status: executing
stopped_at: Completed 09-02-PLAN.md (backend data layer + model field + config endpoint)
last_updated: "2026-04-05T05:46:55.303Z"
last_activity: 2026-04-05
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 13
  completed_plans: 12
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** Given a job listing and a base CV, produce a tailored CV that honestly highlights the most relevant experience and skills — never fabricate, only emphasize and reframe.
**Current focus:** Phase 09 — add-gemini-2-5-flash-as-alternative-ai-provider-with-model-selector-in-vue-ui

## Current Position

Phase: 09 (add-gemini-2-5-flash-as-alternative-ai-provider-with-model-selector-in-vue-ui) — EXECUTING
Plan: 3 of 3
Status: Ready to execute
Last activity: 2026-04-05

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 05 P01 | 174s | 3 tasks | 8 files |
| Phase 05 P02 | 90 | 2 tasks | 5 files |
| Phase 07 P02 | 420 | 2 tasks | 6 files |
| Phase 09 P01 | 480 | 2 tasks | 8 files |
| Phase 09 P02 | 189 | 2 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.0]: AI backend is Claude Code CLI (`claude -p`) — not Gemini. Research SUMMARY.md references Gemini; disregard those SDK recommendations.
- [v1.0/Phase 02]: Single-pass regex escape_latex prevents cascading re-escape of backslashes; must verify against real Claude output when Phase 6 worker calls render_pdf.
- [v1.0/Phase 03]: GapItem lives in models.py so Phase 7 frontend API can import it without pipeline logic.
- [v2.0]: Axios excluded permanently — confirmed supply chain attack (UNC1069, 2026-03-31); use native fetch everywhere.
- [v2.0]: asyncio.to_thread wraps both subprocess.run calls (Claude CLI and latexmk) — must happen in Phase 5 before the job queue is built on top.
- [v2.0]: asyncio.create_task + app-level job registry (not FastAPI BackgroundTasks) — BackgroundTasks has no status-tracking; store Task references to prevent GC.
- [v2.0]: SQLite WAL mode + busy_timeout=5000 required from first write — standard BEGIN DEFERRED makes busy timeout ineffective under concurrent writes.
- [Phase 05]: asyncio.to_thread wraps both run_pipeline and render_pdf in backend/pipeline_runner.py — prevents event loop blocking from subprocess.run calls
- [Phase 05]: db_path parameter added to init_db and get_db for test isolation via pytest tmp_path fixture
- [Phase 05]: Tests use asyncio.run() in sync functions instead of pytest-asyncio — avoids extra dev dependency
- [Phase 05]: asyncio.create_task + module-level set registry (_background_tasks) with done_callback discard — GC-safe task references for Phase 6 job queue
- [Phase 05]: CORSMiddleware with explicit allow_origins=['http://localhost:5173'] (not wildcard) for security during development
- [Phase 05]: lifespan async context manager pattern (not deprecated @app.on_event) for FastAPI startup/shutdown
- [Phase 07]: 30s polling owned by AppSidebar.vue lifecycle (not store.startSidebarPolling) — matches RESEARCH.md Pattern 6, component lifecycle owns the interval
- [Phase 07]: storeToRefs pattern used in AppSidebar for reactive destructuring — prevents reactivity loss when destructuring Pinia setup stores
- [Phase 09]: GeminiProvider instantiated lazily inside get_provider() — missing GEMINI_API_KEY only raises at call time, not server startup
- [Phase 09]: Shared _build_prompt() helper extracted from run_pipeline() so both Claude and Gemini use the identical CV tailoring prompt
- [Phase 09]: Idempotent migration guards ALTER TABLE with PRAGMA table_info check — no error on repeated startups
- [Phase 09]: run_provider_async() added alongside run_pipeline_async() for backward compatibility — tests unchanged
- [Phase 09]: GET /api/config uses os.environ.get with bool() cast — simple feature flag, no Pydantic Settings overhead

### Pending Todos

None yet.

### Roadmap Evolution

- Phase 9 added: Add Gemini 2.5 Flash as alternative AI provider with model selector in Vue UI

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260405-4j5 | Fix stale CLAUDE.md recommended stack section | 2026-04-04 | d49d4bd | [260405-4j5-fix-stale-claude-md-recommended-stack-se](./quick/260405-4j5-fix-stale-claude-md-recommended-stack-se/) |

### Blockers/Concerns

- [Phase 5 → 6]: asyncio.Task done-callback behavior under CancelledError and unhandled exceptions needs a verified implementation before Phase 6 relies on it for all job state updates.
- [Phase 5 → 6]: aiosqlite connection management (per-operation vs single lifespan connection) should be validated with concurrent-write integration test before building the full job queue on top.
- [Phase 5 → 6]: Claude CLI concurrent invocation semaphore value (2-3 max) needs empirical validation under real concurrent load during Phase 6.

## Session Continuity

Last session: 2026-04-05T05:46:55.298Z
Stopped at: Completed 09-02-PLAN.md (backend data layer + model field + config endpoint)
Resume file: None
