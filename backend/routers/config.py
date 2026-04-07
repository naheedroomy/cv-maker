"""Application configuration endpoint — reports feature availability."""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter

from backend.settings_cache import get_api_key

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


@router.get("")
async def get_config():
    """Return feature flags — provider availability based on DB-stored keys, env vars, and CLI presence."""
    return {
        "claude_cli_available": _claude_cli_available(),
        "claude_api_available": bool(await get_api_key("anthropic_api_key")),
        "gemini_available": bool(await get_api_key("gemini_api_key")),
        "openai_available": bool(await get_api_key("openai_api_key")),
    }
