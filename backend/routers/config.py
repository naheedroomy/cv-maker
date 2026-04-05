"""Application configuration endpoint — reports feature availability."""
from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_config():
    """Return feature flags — Gemini and OpenAI API key availability."""
    return {
        "gemini_available": bool(os.environ.get("GEMINI_API_KEY")),
        "openai_available": bool(os.environ.get("OPENAI_API_KEY")),
    }
