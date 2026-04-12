---
phase: 1007-add-gemini-webapi-as-new-ai-provider
plan: 02
subsystem: ui
tags: [vue3, model-selector, settings, gemini-web, cookie-auth]

# Dependency graph
requires:
  - phase: 1007-add-gemini-webapi-as-new-ai-provider plan 01
    provides: Backend GeminiWebProvider, /api/config gemini_web_available flag, /api/settings gemini_web_psid and gemini_web_model fields
provides:
  - Gemini Web pill in ModelSelector with availability gating
  - Gemini Web tab in SettingsView with cookie and model configuration
  - geminiWebAvailable wiring in all 4 ModelSelector consumer views
affects: [1007-03, 1007-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [cookie-based provider availability gating, textarea for long secret values]

key-files:
  created: []
  modified:
    - frontend/src/components/ModelSelector.vue
    - frontend/src/views/SettingsView.vue
    - frontend/src/views/JobFormView.vue
    - frontend/src/views/CvConverterView.vue
    - frontend/src/components/RegeneratePanel.vue
    - frontend/src/components/CoverLetterSection.vue

key-decisions:
  - "Cookie field uses textarea (not input) for ~200+ character __Secure-1PSID values"
  - "gemini_web_psid added to apiKeyFields for masked-value save protection"

patterns-established:
  - "Cookie-based provider: same availability gating pattern as API key providers but with textarea input"

requirements-completed: [GWEB-05, GWEB-06]

# Metrics
duration: 5min
completed: 2026-04-12
---

# Phase 1007 Plan 02: Frontend Gemini Web Integration Summary

**Gemini Web pill added to ModelSelector with cookie-based availability gating and Settings tab for __Secure-1PSID configuration**

## Performance

- **Duration:** 5 min 27s
- **Started:** 2026-04-12T20:35:50Z
- **Completed:** 2026-04-12T20:41:17Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Gemini Web pill appears in ModelSelector alongside Claude API, Gemini, and OpenAI options
- Pill is disabled when user has no __Secure-1PSID cookie configured, enabled when cookie is present
- Settings page has a "Gemini Web" tab with cookie textarea (with clear extraction instructions), model input, and info section
- All 4 ModelSelector consumer views (JobFormView, CvConverterView, RegeneratePanel, CoverLetterSection) wire the geminiWebAvailable flag from /api/config

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Gemini Web pill to ModelSelector and wire availability in all consumer views** - `477e14a` (feat)
2. **Task 2: Add Gemini Web tab to SettingsView with cookie and model inputs** - `1702536` (feat)

## Files Created/Modified
- `frontend/src/components/ModelSelector.vue` - Added geminiWebAvailable prop, gemini-web option, hint text, and disabled check
- `frontend/src/views/SettingsView.vue` - Added Gemini Web tab with cookie textarea, model input, and extraction instructions
- `frontend/src/views/JobFormView.vue` - Wired geminiWebAvailable ref from /api/config to ModelSelector prop
- `frontend/src/views/CvConverterView.vue` - Wired geminiWebAvailable ref from /api/config to ModelSelector prop
- `frontend/src/components/RegeneratePanel.vue` - Wired geminiWebAvailable ref from /api/config to ModelSelector prop
- `frontend/src/components/CoverLetterSection.vue` - Wired geminiWebAvailable ref from /api/config to ModelSelector prop, added gemini-web to model display map

## Decisions Made
- Cookie field uses textarea (not input) because __Secure-1PSID values are ~200+ characters, too long for a single-line input
- gemini_web_psid added to apiKeyFields array so masked values (***xxxx) are not re-sent to backend on save

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added gemini-web to CoverLetterSection model display map**
- **Found during:** Task 1 (CoverLetterSection.vue wiring)
- **Issue:** CoverLetterSection has a model display map for history badges that maps model IDs to human labels (e.g., 'claude-api' -> 'Claude'). Without adding 'gemini-web', the badge would show the raw ID string.
- **Fix:** Added `'gemini-web': 'Gemini Web'` to the display map object
- **Files modified:** frontend/src/components/CoverLetterSection.vue
- **Verification:** Grep confirms entry present
- **Committed in:** 477e14a (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Minor display completeness fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data sources are wired to the /api/config and /api/settings endpoints.

## Next Phase Readiness
- Frontend UI is complete for Gemini Web provider selection and configuration
- Backend provider (Plan 01) and frontend (Plan 02) are connected via /api/config and /api/settings
- Ready for Plan 03 (if any) or end-to-end testing

---
*Phase: 1007-add-gemini-webapi-as-new-ai-provider*
*Completed: 2026-04-12*

## Self-Check: PASSED
All 6 modified files exist. SUMMARY.md created. Both task commits (477e14a, 1702536) verified in git log.
