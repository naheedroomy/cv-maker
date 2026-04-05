---
phase: 09-add-gemini-2-5-flash-as-alternative-ai-provider-with-model-selector-in-vue-ui
plan: 01
subsystem: api
tags: [google-genai, gemini, strategy-pattern, providers, pipeline, python]

# Dependency graph
requires:
  - phase: 08-monorepo-serve-spa-from-fastapi
    provides: Working FastAPI backend and pipeline.py with run_pipeline()
provides:
  - Strategy-pattern provider abstraction with BaseProvider ABC
  - ClaudeProvider wrapping existing run_pipeline()
  - GeminiProvider using google-genai SDK with 3-attempt retry
  - get_provider() factory function for model-based routing
  - _build_prompt() shared prompt helper extracted from pipeline.py
  - google-genai>=1.70.0 installed in project dependencies
affects:
  - 09-02 (backend schema + DB migration — uses get_provider())
  - 09-03 (Vue UI model selector — depends on Gemini being available)

# Tech tracking
tech-stack:
  added: [google-genai>=1.70.0]
  patterns:
    - Strategy pattern for AI provider abstraction (BaseProvider ABC + concrete subclasses)
    - Lazy provider instantiation inside factory (never at module scope)
    - Shared prompt helper (_build_prompt) separating prompt construction from invocation

key-files:
  created:
    - src/cv_maker/providers/__init__.py
    - src/cv_maker/providers/base.py
    - src/cv_maker/providers/claude_provider.py
    - src/cv_maker/providers/gemini_provider.py
  modified:
    - src/cv_maker/pipeline.py
    - pyproject.toml
    - uv.lock
    - tests/test_pipeline.py

key-decisions:
  - "GeminiProvider instantiated lazily inside get_provider() — never at module scope — so missing GEMINI_API_KEY only raises at call time, not server startup"
  - "Shared _build_prompt() helper extracted from run_pipeline() so both Claude and Gemini use the identical CV tailoring prompt"
  - "ClaudeProvider delegates entirely to existing run_pipeline() — zero duplication, backward compatible"
  - "GeminiProvider uses same 3-attempt retry pattern as Claude for consistency"

patterns-established:
  - "Provider Strategy Pattern: BaseProvider ABC in providers/base.py; ClaudeProvider/GeminiProvider as concrete implementations; get_provider() factory in providers/__init__.py"
  - "Lazy instantiation: providers are created inside get_provider(), never at module scope, to prevent startup failures from missing environment variables"

requirements-completed: [GEMINI-01, GEMINI-02, GEMINI-03, GEMINI-04]

# Metrics
duration: 8min
completed: 2026-04-05
---

# Phase 9 Plan 01: Provider Abstraction Layer Summary

**Strategy-pattern providers/ package with BaseProvider ABC, ClaudeProvider (delegating to run_pipeline), and GeminiProvider (google-genai SDK) sharing a single extracted _build_prompt helper**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-05T05:30:00Z
- **Completed:** 2026-04-05T05:38:01Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Installed google-genai>=1.70.0 SDK via uv add
- Extracted _build_prompt(base_cv, job_text) -> str from run_pipeline() as a shared helper; run_pipeline() behavior is unchanged
- Created providers/ package: BaseProvider ABC, ClaudeProvider (thin wrapper), GeminiProvider (google-genai SDK, 3-attempt retry, lazy init)
- get_provider() factory defaults to ClaudeProvider for any unknown model string
- All pipeline tests pass (14 passed); ruff check passes on providers/

## Task Commits

Each task was committed atomically:

1. **Task 1: Install google-genai and extract _build_prompt from pipeline.py** - `5fbe70b` (feat)
2. **Task 2: Create providers/ package with BaseProvider, ClaudeProvider, GeminiProvider, and factory** - `06f0e72` (feat)

## Files Created/Modified

- `src/cv_maker/providers/__init__.py` - Factory function get_provider() and re-exports
- `src/cv_maker/providers/base.py` - BaseProvider ABC with run() abstract method
- `src/cv_maker/providers/claude_provider.py` - ClaudeProvider delegating to run_pipeline()
- `src/cv_maker/providers/gemini_provider.py` - GeminiProvider with google-genai SDK, 3-attempt retry
- `src/cv_maker/pipeline.py` - _build_prompt() extracted; run_pipeline() now calls _build_prompt()
- `pyproject.toml` - Added google-genai>=1.70.0 dependency
- `uv.lock` - Updated lockfile
- `tests/test_pipeline.py` - Updated to match single-call pipeline (see deviations)

## Decisions Made

- GeminiProvider reads GEMINI_API_KEY at `__init__` time (lazy instantiation inside factory) — not at module import — so a missing API key only surfaces when a user actually selects Gemini; server starts normally without it
- ClaudeProvider is a thin wrapper around run_pipeline() — no code duplication; existing pipeline behavior fully preserved
- _build_prompt() is private (underscore prefix) but is imported by GeminiProvider from pipeline — this is an intentional internal API boundary

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing test failures in test_pipeline.py**
- **Found during:** Task 1 (verifying pipeline tests pass)
- **Issue:** tests/test_pipeline.py imported `analyze_job` and `tailor_cv` from pipeline.py — functions that were removed in the v2.0 combined-pipeline refactor (commit 6052a02). The test file was never updated when pipeline was simplified to a single combined Claude call. Tests were failing with ImportError before any changes in this plan.
- **Fix:** Rewrote test_pipeline.py to test the actual single-call pipeline: removed all analyze_job/tailor_cv tests, replaced with _build_prompt unit tests and updated run_pipeline tests using a single TAILORED_CV_JSON fixture (matching the combined output schema)
- **Files modified:** tests/test_pipeline.py
- **Verification:** 14 tests pass
- **Committed in:** 5fbe70b (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug fix for pre-existing test failures)
**Impact on plan:** Necessary correction of stale tests from the v2.0 pipeline refactor. No scope creep. Tests now accurately reflect the single-call combined pipeline behavior.

## Issues Encountered

None beyond the pre-existing test failures which were resolved as part of Task 1.

## User Setup Required

None - no external service configuration required for this plan. GEMINI_API_KEY is needed at runtime when Gemini is used (handled in 09-02/09-03).

## Next Phase Readiness

- providers/ package is complete and ready for 09-02 (backend schema extension + DB migration)
- 09-02 will import get_provider() from cv_maker.providers and route jobs through it based on the model field
- GEMINI_API_KEY is not set in this environment — Gemini cannot be tested end-to-end until 09-03 adds the UI and user sets the key

---
*Phase: 09-add-gemini-2-5-flash-as-alternative-ai-provider-with-model-selector-in-vue-ui*
*Completed: 2026-04-05*
