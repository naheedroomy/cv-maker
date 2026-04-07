---
phase: quick
plan: 260407-qcs
subsystem: settings, providers, frontend
tags: [api-keys, settings, db-override, masking, job-listing-tab]
dependency_graph:
  requires: []
  provides:
    - API key CRUD via Settings panel with DB persistence
    - DB-overrides-.env key resolution in all providers
    - Masked GET responses for API keys
    - Dedicated Job Listing tab in JobDetailView
  affects:
    - backend/settings_cache.py
    - backend/routers/settings.py
    - backend/routers/config.py
    - core/providers/claude_api_provider.py
    - core/providers/gemini_provider.py
    - core/providers/openai_provider.py
    - frontend/src/views/SettingsView.vue
    - frontend/src/views/JobDetailView.vue
tech_stack:
  added: []
  patterns:
    - DB-overrides-.env for API key resolution via get_api_key()
    - Masked key display (***last4) on GET to avoid exposing secrets in browser
    - Password input fields for API keys in provider settings tabs
key_files:
  created: []
  modified:
    - backend/settings_cache.py
    - backend/routers/settings.py
    - backend/routers/config.py
    - core/providers/claude_api_provider.py
    - core/providers/gemini_provider.py
    - core/providers/openai_provider.py
    - frontend/src/views/SettingsView.vue
    - frontend/src/views/JobDetailView.vue
decisions:
  - key: get_api_key helper centralizes DB-overrides-.env logic
    why: Single function handles the fallback chain for all 3 API keys; providers and config endpoint import one function instead of duplicating env-var logic
  - key: Masked GET responses return ***last4 chars, never full key
    why: Browser DevTools / network logs should never expose the full key; last 4 chars confirm which key is stored without revealing it
  - key: handleSave skips masked fields (starts with ***) on PUT
    why: After page reload, GET returns masked values; sending them as-is would overwrite the stored key with the mask string — omitting preserves the original key
metrics:
  duration: 215s
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_modified: 8
---

# Quick Task 260407-qcs: API Key Management in Settings + Job Listing Tab

**One-liner:** DB-persisted API key CRUD in Settings panel with masked GET responses and DB-overrides-.env provider fallback; dedicated Job Listing tab moved out of Analysis.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backend — API key storage, config availability, provider fallback | 1388f7c | backend/settings_cache.py, backend/routers/settings.py, backend/routers/config.py, 3 providers |
| 2 | Frontend — API key inputs in Settings + Job Listing tab | 442bb5d | frontend/src/views/SettingsView.vue, frontend/src/views/JobDetailView.vue |

## What Was Built

### Backend Changes

**`backend/settings_cache.py`**
- Added `anthropic_api_key`, `gemini_api_key`, `openai_api_key` to `_DEFAULTS` (empty strings)
- Added `_API_KEY_ENV_MAP` mapping settings keys to their corresponding env variable names
- Added `get_api_key(key)` function: returns DB-stored value if non-empty, otherwise falls back to `os.environ.get(env_var)` — centralizes the "DB overrides .env" logic for all callers

**`backend/routers/settings.py`**
- Extended `SettingsResponse` and `SettingsUpdate` with `anthropic_api_key`, `gemini_api_key`, `openai_api_key`
- Added `_mask_key()` helper: returns `"***" + key[-4:]` for non-empty keys, empty string otherwise
- `get_settings()` returns masked API key values for display safety; never exposes full keys

**`backend/routers/config.py`**
- Replaced `bool(os.environ.get("ANTHROPIC_API_KEY"))` pattern with `bool(get_api_key("anthropic_api_key"))` for all 3 providers
- Claude CLI availability remains independent (runtime `_claude_cli_available()` check)
- Removed unused `import os`

**Providers (all 3)**
- `claude_api_provider.py`: `get_api_key("anthropic_api_key")` replaces `os.environ.get("ANTHROPIC_API_KEY")`
- `gemini_provider.py`: `get_api_key("gemini_api_key")` replaces `os.environ.get("GEMINI_API_KEY")`
- `openai_provider.py`: `get_api_key("openai_api_key")` replaces `os.environ.get("OPENAI_API_KEY")`
- All keep the `if not api_key: raise RuntimeError(...)` guard with updated message

### Frontend Changes

**`frontend/src/views/SettingsView.vue`**
- Updated `Settings` interface with `anthropic_api_key`, `gemini_api_key`, `openai_api_key` fields
- Claude API tab: password input for `anthropic_api_key` (placeholder `sk-ant-...`)
- Gemini tab: password input for `gemini_api_key` (placeholder `AIza...`)
- OpenAI tab: password input for `openai_api_key` (placeholder `sk-...`)
- Claude CLI tab: unchanged — "No API key needed" text remains
- `handleSave`: filters out API key fields starting with `***` before PUT — masked values are not sent to the backend, preserving the stored key
- Subtitle updated to "Configure model names, endpoints, and API keys for each provider."

**`frontend/src/views/JobDetailView.vue`**
- `activeTab` type extended: `'cv' | 'cover-letter' | 'analysis' | 'job-listing'`
- Added "Job Listing" tab button in the tab bar (4th position)
- Moved `job_text` section from the Analysis tab panel into a new dedicated Job Listing tab panel
- Analysis tab empty-state condition no longer checks `!currentJob.job_text`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `import os` from providers**
- **Found during:** Task 1 — after replacing `os.environ.get()` calls, `os` was no longer imported in any of the 3 providers
- **Fix:** Removed the now-unused `import os` line from `claude_api_provider.py`, `gemini_provider.py`, and `openai_provider.py`
- **Files modified:** All 3 provider files
- **Commit:** 1388f7c

None beyond the above cleanup.

## Known Stubs

None — all functionality is fully wired. API keys flow: Settings UI -> PUT /api/settings -> DB -> settings_cache -> get_api_key() -> providers and config endpoint.

## Self-Check: PASSED
