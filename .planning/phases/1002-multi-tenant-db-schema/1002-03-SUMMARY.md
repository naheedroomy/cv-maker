# Summary: 1002-03 — Router & Worker Wiring — Thread user_id Through All DB Queries

## Result: COMPLETE

All 7 tasks executed successfully. Every SQL query that touches user-owned data now includes `user_id=?` filtering. Provider constructors accept explicit parameters; settings resolution moved to the async `get_provider()` factory. The in-process settings cache is fully eliminated from the startup path.

## Tasks Completed

| Task | Title | Commit |
|------|-------|--------|
| T1 | Add user_id scoping to jobs.py router (10 SQL queries) | 0e2b29f |
| T2 | Add user_id scoping to settings.py router, remove update_cache | 2965044 |
| T3 | Add user_id scoping to cover_letter.py router (5 SQL queries) | d2a359f |
| T4 | Await async get_api_key() in config.py router | ad17739 |
| T5 | Refactor providers: constructor params + async get_provider() | 24f294d |
| T6 | Await async get_provider() and get_setting() in worker.py | edec0d8 |
| T7 | Remove load_settings() from main.py lifespan | df883a6 |

## Files Modified (11)

- `backend/routers/jobs.py` — ANONYMOUS_USER_ID in all 10 SQL queries
- `backend/routers/settings.py` — user_id-scoped SELECT/INSERT with composite PK ON CONFLICT
- `backend/routers/cover_letter.py` — user_id filtering in all 5 SQL queries
- `backend/routers/config.py` — await async get_api_key() calls
- `core/providers/__init__.py` — async get_provider() factory with lazy imports
- `core/providers/claude_api_provider.py` — constructor accepts api_key, model params
- `core/providers/claude_provider.py` — constructor accepts cli_model param
- `core/providers/gemini_provider.py` — constructor accepts api_key, model params
- `core/providers/openai_provider.py` — constructor accepts api_key, model, base_url params
- `core/pipeline.py` — cli_model threaded through run_pipeline → _invoke_with_retry → _invoke_claude
- `backend/worker.py` — await async get_provider() and get_setting()
- `backend/main.py` — removed load_settings() and settings_cache import

## Decisions

- Provider constructors accept explicit params instead of importing settings_cache — enables async resolution and removes coupling between core/ and backend/
- `_get_claude_cli_model()` fallback preserved in pipeline.py for backward compatibility when cli_model is empty
- `core/cover_letter.py` and `core/cv_converter.py` still use sync `get_provider()` — out of scope for this plan, will need updating when those features thread through multi-tenant model

## Verification

- ✅ All routers import and use ANONYMOUS_USER_ID
- ✅ No settings_cache imports in any provider file
- ✅ load_settings and update_cache fully removed from backend/
- ✅ Import smoke test passes: `from backend.main import app`
