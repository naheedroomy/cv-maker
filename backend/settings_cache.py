"""Per-user settings lookup — queries DB directly (no cache).

All lookups accept a user_id parameter. When omitted, ANONYMOUS_USER_ID is used.
Phase 1003 will pass the real JWT user's ID.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "claude_cli_model": "haiku",
    "claude_api_model": "claude-haiku-4-5",
    "gemini_model": "gemini-2.5-flash",
    "openai_model": "gpt-4o-mini",
    "openai_base_url": "",
    "cv_filename": "",
    "anthropic_api_key": "",
    "gemini_api_key": "",
    "openai_api_key": "",
    "gemini_web_psid": "",
    "gemini_web_model": "gemini-3-pro",
    # "staged" = multi-stage pipeline (requirements -> evidence map -> generation)
    # with automatic fallback to single-shot; "single" forces single-shot only.
    "pipeline_mode": "staged",
}

# Mapping from settings key -> environment variable name
_API_KEY_ENV_MAP = {
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "gemini_api_key": "GEMINI_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
    "gemini_web_psid": "GEMINI_WEB_PSID",
}


async def get_setting(key: str, user_id: int | None = None) -> str:
    """Get a setting value from DB for the given user. Falls back to default."""
    from backend.db import ANONYMOUS_USER_ID, get_db

    uid = user_id if user_id is not None else ANONYMOUS_USER_ID
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE user_id=? AND key=?",
            (uid, key),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()
    if row:
        return row["value"]
    return _DEFAULTS.get(key, "")


async def get_api_key(key: str, user_id: int | None = None) -> str:
    """Get an API key: DB value (per user) > env var > empty string."""
    db_val = await get_setting(key, user_id)
    if db_val:
        return db_val
    env_var = _API_KEY_ENV_MAP.get(key, "")
    return os.environ.get(env_var, "") if env_var else ""
