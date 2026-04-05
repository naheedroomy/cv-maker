"""Application configuration endpoint — reports feature availability."""
from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_config():
    """Return feature flags — currently just Gemini API key availability."""
    return {"gemini_available": bool(os.environ.get("GEMINI_API_KEY"))}
