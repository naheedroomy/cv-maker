"""Provider settings API — GET/PUT model names and base URLs."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.auth import get_current_user
from backend.db import get_db
from backend.settings_cache import _DEFAULTS, get_setting

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    claude_cli_model: str
    claude_api_model: str
    gemini_model: str
    openai_model: str
    openai_base_url: str
    cv_filename: str
    anthropic_api_key: str
    gemini_api_key: str
    openai_api_key: str
    gemini_web_psid: str
    gemini_web_model: str


class SettingsUpdate(BaseModel):
    claude_cli_model: str | None = None
    claude_api_model: str | None = None
    gemini_model: str | None = None
    openai_model: str | None = None
    openai_base_url: str | None = None
    cv_filename: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_web_psid: str | None = None
    gemini_web_model: str | None = None


def _mask_key(key: str) -> str:
    """Return masked version of an API key for display safety.

    Returns '***' + last 4 chars if non-empty, otherwise empty string.
    """
    if not key:
        return ""
    return "***" + key[-4:]


@router.get("", response_model=SettingsResponse)
async def get_settings(user: dict = Depends(get_current_user)) -> SettingsResponse:
    """Return current provider settings (model names + base URLs + masked API keys)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT key, value FROM settings WHERE user_id=?",
            (user["id"],),
        )
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
        cv_filename=stored.get("cv_filename", _DEFAULTS["cv_filename"]),
        anthropic_api_key=_mask_key(stored.get("anthropic_api_key", _DEFAULTS["anthropic_api_key"])),
        gemini_api_key=_mask_key(stored.get("gemini_api_key", _DEFAULTS["gemini_api_key"])),
        openai_api_key=_mask_key(stored.get("openai_api_key", _DEFAULTS["openai_api_key"])),
        gemini_web_psid=_mask_key(stored.get("gemini_web_psid", _DEFAULTS["gemini_web_psid"])),
        gemini_web_model=stored.get("gemini_web_model", _DEFAULTS["gemini_web_model"]),
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate, user: dict = Depends(get_current_user)) -> SettingsResponse:
    """Update provider settings. Only provided fields are updated."""
    db = await get_db()
    try:
        updates = body.model_dump(exclude_none=True)
        for key, value in updates.items():
            await db.execute(
                "INSERT INTO settings (user_id, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value",
                (user["id"], key, value),
            )
        await db.commit()
    finally:
        await db.close()

    return await get_settings(user=user)


@router.post("/check-gemini-web")
async def check_gemini_web(user: dict = Depends(get_current_user)):
    """Quick connectivity check for Gemini Web cookie."""
    psid = await get_setting("gemini_web_psid", user["id"])
    if not psid:
        return {"ok": False, "error": "No cookie configured"}

    async def _test():
        from gemini_webapi import GeminiClient
        client = GeminiClient(psid, "")
        await client.init(timeout=15, auto_close=True, close_delay=10, auto_refresh=False)
        try:
            resp = await client.generate_content("Reply with exactly: OK")
            return resp.text
        finally:
            await client.close()

    try:
        text = await asyncio.wait_for(_test(), timeout=20)
        return {"ok": True, "response": text[:100]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}
