"""In-memory settings cache — avoids DB reads on every provider instantiation.

Loaded once at startup and refreshed on PUT /api/settings.
Providers call get_setting(key) which returns the cached value.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_cache: dict[str, str] = {}

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
}

# Mapping from settings key → environment variable name
_API_KEY_ENV_MAP = {
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "gemini_api_key": "GEMINI_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
}


async def load_settings() -> None:
    """Load all settings from DB into memory. Call on startup."""
    from backend.db import get_db

    db = await get_db()
    try:
        cursor = await db.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
    finally:
        await db.close()

    _cache.clear()
    for row in rows:
        _cache[row["key"]] = row["value"]
    logger.info("Settings cache loaded: %d entries", len(_cache))


def get_setting(key: str) -> str:
    """Get a setting value. Returns cached DB value, or default."""
    return _cache.get(key) or _DEFAULTS.get(key, "")


def get_api_key(key: str) -> str:
    """Get an API key with DB-overrides-.env semantics.

    Returns the DB-stored key (via get_setting) if non-empty,
    otherwise falls back to the corresponding environment variable.
    """
    db_val = get_setting(key)
    if db_val:
        return db_val
    env_var = _API_KEY_ENV_MAP.get(key, "")
    return os.environ.get(env_var, "") if env_var else ""


def update_cache(key: str, value: str) -> None:
    """Update a single cached value (called after DB write)."""
    _cache[key] = value
