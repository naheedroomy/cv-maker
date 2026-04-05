# src/cv_maker/providers/__init__.py
# Provider factory and re-exports.
# IMPORTANT: GeminiProvider is instantiated lazily inside get_provider() — NEVER at module scope.
# This ensures a missing GEMINI_API_KEY only raises an error when Gemini is actually requested,
# not at server startup.
from __future__ import annotations

from cv_maker.providers.base import BaseProvider
from cv_maker.providers.claude_provider import ClaudeProvider
from cv_maker.providers.gemini_provider import GeminiProvider

__all__ = ["BaseProvider", "ClaudeProvider", "GeminiProvider", "get_provider"]


def get_provider(model: str) -> BaseProvider:
    """Factory function: return the appropriate provider for the given model string.

    Supported values:
    - "gemini-flash" → GeminiProvider (requires GEMINI_API_KEY)
    - "claude-haiku" → ClaudeProvider (default)
    - any unknown value → ClaudeProvider (fallback)
    """
    if model == "gemini-flash":
        return GeminiProvider()
    return ClaudeProvider()  # default for "claude-haiku" and any unknown value
