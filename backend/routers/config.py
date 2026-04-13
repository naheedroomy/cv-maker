"""Application configuration endpoint — reports feature availability."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Header

from backend.settings_cache import get_setting

router = APIRouter(prefix="/config", tags=["config"])


def _claude_cli_available() -> bool:
    """Check if Claude CLI is installed and .claude dir has content (likely authed)."""
    if not shutil.which("claude"):
        return False
    claude_dir = Path.home() / ".claude"
    if not claude_dir.is_dir():
        return False
    # Empty mount → no auth; any files means host .claude was mounted
    return any(claude_dir.iterdir())


def _extract_user_id(authorization: str | None) -> int | None:
    """Best-effort user_id extraction from JWT. Returns None if no valid token."""
    if not authorization:
        return None
    import jwt as pyjwt
    token = authorization.removeprefix("Bearer ").strip()
    try:
        secret = os.environ.get("JWT_SECRET", "dev-secret-change-me")
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("user_id")
    except Exception:
        return None


@router.get("")
async def get_config(authorization: str | None = Header(None, alias="Authorization")):
    """Return feature flags — provider availability based on the current user's DB keys.

    This endpoint is intentionally public (no 401 on missing token) so the
    sign-in page can fetch google_client_id. When a valid JWT is present,
    it checks that user's API keys for provider availability.
    """
    user_id = _extract_user_id(authorization)

    # Only check user-level keys (DB), not server env vars.
    # Server GEMINI_API_KEY is for PDF parsing only — not for CV tailoring.
    return {
        "claude_api_available": bool(await get_setting("anthropic_api_key", user_id)),
        "gemini_available": bool(await get_setting("gemini_api_key", user_id)),
        "openai_available": bool(await get_setting("openai_api_key", user_id)),
        "gemini_web_available": bool(await get_setting("gemini_web_psid", user_id)),
        "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
    }
