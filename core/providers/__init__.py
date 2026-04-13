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


async def get_provider(model: str, user_id: int | None = None) -> BaseProvider:
    """Async factory: resolve per-user settings, then construct the provider.

    Supported values:
    - "claude-api" -> ClaudeAPIProvider (requires ANTHROPIC_API_KEY)
    - "gemini-flash" -> GeminiProvider (requires GEMINI_API_KEY)
    - "gemini-web" -> GeminiWebProvider (requires __Secure-1PSID cookie)
    - "openai" -> OpenAIProvider (requires OPENAI_API_KEY)
    - "claude-haiku" -> ClaudeProvider (default, uses CLI)
    - any unknown value -> ClaudeProvider (fallback)
    """
    from backend.settings_cache import get_setting

    # Only use per-user keys (from DB) for tailoring providers.
    # Server env vars (GEMINI_API_KEY etc.) are for internal use (PDF parsing) only.
    if model == "claude-api":
        from core.providers.claude_api_provider import ClaudeAPIProvider
        api_key = await get_setting("anthropic_api_key", user_id)
        api_model = await get_setting("claude_api_model", user_id)
        return ClaudeAPIProvider(api_key=api_key, model=api_model)
    if model == "gemini-flash":
        from core.providers.gemini_provider import GeminiProvider
        api_key = await get_setting("gemini_api_key", user_id)
        gem_model = await get_setting("gemini_model", user_id)
        return GeminiProvider(api_key=api_key, model=gem_model)
    if model == "openai":
        from core.providers.openai_provider import OpenAIProvider
        api_key = await get_setting("openai_api_key", user_id)
        oai_model = await get_setting("openai_model", user_id)
        base_url = (await get_setting("openai_base_url", user_id)) or None
        return OpenAIProvider(api_key=api_key, model=oai_model, base_url=base_url)
    if model == "gemini-web":
        from core.providers.gemini_web_provider import GeminiWebProvider
        psid = await get_setting("gemini_web_psid", user_id)
        web_model = await get_setting("gemini_web_model", user_id)
        return GeminiWebProvider(psid=psid, model=web_model)
    # Default: "claude-haiku" and any unknown value
    from core.providers.claude_provider import ClaudeProvider
    cli_model = await get_setting("claude_cli_model", user_id)
    return ClaudeProvider(cli_model=cli_model)
