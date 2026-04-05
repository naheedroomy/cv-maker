"""Provider settings API — GET/PUT model names and base URLs."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.db import get_db
from backend.settings_cache import update_cache

router = APIRouter(prefix="/settings", tags=["settings"])

# Defaults — used when no DB value exists
_DEFAULTS = {
    "claude_api_model": "claude-haiku-4-5",
    "gemini_model": "gemini-2.5-flash",
    "openai_model": "gpt-4o-mini",
    "openai_base_url": "",
}


class SettingsResponse(BaseModel):
    claude_cli_model: str
    claude_api_model: str
    gemini_model: str
    openai_model: str
    openai_base_url: str


class SettingsUpdate(BaseModel):
    claude_cli_model: str | None = None
    claude_api_model: str | None = None
    gemini_model: str | None = None
    openai_model: str | None = None
    openai_base_url: str | None = None


@router.get("", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    """Return current provider settings (model names + base URLs)."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
    finally:
        await db.close()

    stored = {row["key"]: row["value"] for row in rows}
    return SettingsResponse(
        claude_cli_model=stored.get("claude_cli_model", _DEFAULTS["claude_cli_model"]),
        claude_api_model=stored.get("claude_api_model", _DEFAULTS["claude_api_model"]),
        gemini_model=stored.get("gemini_model", _DEFAULTS["gemini_model"]),
        openai_model=stored.get("openai_model", _DEFAULTS["openai_model"]),
        openai_base_url=stored.get("openai_base_url", _DEFAULTS["openai_base_url"]),
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate) -> SettingsResponse:
    """Update provider settings. Only provided fields are updated."""
    db = await get_db()
    try:
        updates = body.model_dump(exclude_none=True)
        for key, value in updates.items():
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            update_cache(key, value)
        await db.commit()
    finally:
        await db.close()

    return await get_settings()
