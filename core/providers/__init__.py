# core/providers/__init__.py
# Provider factory and re-exports.
# IMPORTANT: Provider classes are imported lazily inside get_provider() — NEVER at module scope.
# This ensures a missing API key only raises an error when that provider is actually requested,
# not at server startup.
from __future__ import annotations

from core.providers.base import BaseProvider

__all__ = [
    "BaseProvider",
    "get_provider",
]


async def get_provider(model: str) -> BaseProvider:
    """Async factory: resolve per-user settings, then construct the provider.

    Supported values:
    - "claude-api" → ClaudeAPIProvider (requires ANTHROPIC_API_KEY)
    - "gemini-flash" → GeminiProvider (requires GEMINI_API_KEY)
    - "openai" → OpenAIProvider (requires OPENAI_API_KEY)
    - "claude-haiku" → ClaudeProvider (default, uses CLI)
    - any unknown value → ClaudeProvider (fallback)
    """
    from backend.settings_cache import get_setting

    # Only use per-user keys (from DB) for tailoring providers.
    # Server env vars (GEMINI_API_KEY etc.) are for internal use (PDF parsing) only.
    if model == "claude-api":
        from core.providers.claude_api_provider import ClaudeAPIProvider
        api_key = await get_setting("anthropic_api_key")
        api_model = await get_setting("claude_api_model")
        return ClaudeAPIProvider(api_key=api_key, model=api_model)
    if model == "gemini-flash":
        from core.providers.gemini_provider import GeminiProvider
        api_key = await get_setting("gemini_api_key")
        gem_model = await get_setting("gemini_model")
        return GeminiProvider(api_key=api_key, model=gem_model)
    if model == "openai":
        from core.providers.openai_provider import OpenAIProvider
        api_key = await get_setting("openai_api_key")
        oai_model = await get_setting("openai_model")
        base_url = (await get_setting("openai_base_url")) or None
        return OpenAIProvider(api_key=api_key, model=oai_model, base_url=base_url)
    # Default: "claude-haiku" and any unknown value
    from core.providers.claude_provider import ClaudeProvider
    cli_model = await get_setting("claude_cli_model")
    return ClaudeProvider(cli_model=cli_model)
