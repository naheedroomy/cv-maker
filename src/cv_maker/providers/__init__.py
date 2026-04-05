# src/cv_maker/providers/__init__.py
# Provider factory and re-exports.
# IMPORTANT: GeminiProvider is instantiated lazily inside get_provider() — NEVER at module scope.
# This ensures a missing GEMINI_API_KEY only raises an error when Gemini is actually requested,
# not at server startup.
from __future__ import annotations

from cv_maker.providers.base import BaseProvider
from cv_maker.providers.claude_api_provider import ClaudeAPIProvider
from cv_maker.providers.claude_provider import ClaudeProvider
from cv_maker.providers.gemini_provider import GeminiProvider
from cv_maker.providers.openai_provider import OpenAIProvider

__all__ = [
    "BaseProvider",
    "ClaudeAPIProvider",
    "ClaudeProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "get_provider",
]


def get_provider(model: str) -> BaseProvider:
    """Factory function: return the appropriate provider for the given model string.

    Supported values:
    - "claude-api" → ClaudeAPIProvider (requires ANTHROPIC_API_KEY)
    - "gemini-flash" → GeminiProvider (requires GEMINI_API_KEY)
    - "openai" → OpenAIProvider (requires OPENAI_API_KEY)
    - "claude-haiku" → ClaudeProvider (default, uses CLI)
    - any unknown value → ClaudeProvider (fallback)
    """
    if model == "claude-api":
        return ClaudeAPIProvider()
    if model == "gemini-flash":
        return GeminiProvider()
    if model == "openai":
        return OpenAIProvider()
    return ClaudeProvider()  # default for "claude-haiku" and any unknown value
