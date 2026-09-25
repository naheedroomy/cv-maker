"""Dynamic model discovery for AI providers via official SDKs."""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# Curated fallback models when API keys are not provided or calls fail
FALLBACK_MODELS: dict[str, list[dict[str, str]]] = {
    "gemini": [
        {"id": "gemini-3.8-flash", "label": "Gemini 3.8 Flash"},
        {"id": "gemini-3-flash-preview", "label": "Gemini 3 Flash Preview"},
        {"id": "gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro Preview"},
        {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash"},
        {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro"},
    ],
    "claude-api": [
        {"id": "claude-haiku-4-5", "label": "Claude Haiku 4.5"},
        {"id": "claude-sonnet-5", "label": "Claude Sonnet 5"},
        {"id": "claude-opus-5-5", "label": "Claude Opus 5.5"},
        {"id": "claude-3-7-sonnet", "label": "Claude 3.7 Sonnet"},
    ],
    "openai": [
        {"id": "gpt-6-sol", "label": "GPT-6 Sol"},
        {"id": "gpt-6-luna", "label": "GPT-6 Luna"},
        {"id": "gpt-5.6-sol", "label": "GPT-5.6 Sol"},
        {"id": "gpt-4o-mini", "label": "GPT-4o Mini"},
        {"id": "gpt-4o", "label": "GPT-4o"},
    ],
    "claude-cli": [
        {"id": "haiku", "label": "Haiku (Default)"},
        {"id": "sonnet", "label": "Sonnet"},
        {"id": "opus", "label": "Opus"},
    ],
    "gemini-web": [
        {"id": "gemini-3-flash", "label": "Gemini 3 Flash"},
        {"id": "gemini-3-pro", "label": "Gemini 3 Pro"},
    ],
}


def _fetch_gemini_models_sync(api_key: str) -> list[dict[str, str]]:
    from google import genai

    client = genai.Client(api_key=api_key)
    raw_models = client.models.list()

    exclude_patterns = ["embedding", "embed", "imagen", "aqa", "robotics", "banana", "nano"]
    discovered: list[dict[str, str]] = []

    for m in raw_models:
        name = getattr(m, "name", "") or ""
        clean_id = name.replace("models/", "").strip()
        if not clean_id.lower().startswith("gemini-"):
            continue
        if any(pat in clean_id.lower() for pat in exclude_patterns):
            continue

        label = getattr(m, "display_name", "") or clean_id
        discovered.append({"id": clean_id, "label": label})

    # Sort descending by id so newer/higher versions appear near the top
    discovered.sort(key=lambda x: x["id"], reverse=True)
    return discovered


def _fetch_claude_models_sync(api_key: str) -> list[dict[str, str]]:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    page = client.models.list()
    raw_models = getattr(page, "data", []) or list(page)

    discovered: list[dict[str, str]] = []
    for m in raw_models:
        m_id = getattr(m, "id", "") or ""
        if not m_id:
            continue
        label = getattr(m, "display_name", "") or m_id
        discovered.append({"id": m_id, "label": label})

    discovered.sort(key=lambda x: x["label"])
    return discovered


def _fetch_openai_models_sync(api_key: str, base_url: str | None = None) -> list[dict[str, str]]:
    import openai

    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    page = client.models.list()
    raw_models = getattr(page, "data", []) or list(page)

    exclude_patterns = [
        "embedding",
        "whisper",
        "tts",
        "dall-e",
        "moderation",
        "babbage",
        "davinci",
        "realtime",
        "audio",
        "transcription",
    ]

    discovered: list[dict[str, str]] = []
    for m in raw_models:
        m_id = getattr(m, "id", "") or ""
        lower_id = m_id.lower()
        if any(pat in lower_id for pat in exclude_patterns):
            continue
        # Only include chat / reasoning models
        if (
            lower_id.startswith("gpt-")
            or lower_id.startswith("o1")
            or lower_id.startswith("o3")
            or lower_id.startswith("o4")
            or lower_id.startswith("chat-")
        ):
            discovered.append({"id": m_id, "label": m_id})

    discovered.sort(key=lambda x: x["id"], reverse=True)
    return discovered


async def discover_provider_models(
    provider: str,
    api_key: str = "",
    base_url: str | None = None,
) -> list[dict[str, str]]:
    """Discover available models for a given provider.

    Returns a list of dicts with 'id' and 'label'.
    Falls back to a curated list if the call fails or api_key is empty.
    """
    prov = provider.lower()
    if prov in ("gemini-flash", "gemini"):
        prov_key = "gemini"
    elif prov in ("claude", "claude-api"):
        prov_key = "claude-api"
    elif prov == "openai":
        prov_key = "openai"
    elif prov == "claude-cli":
        return FALLBACK_MODELS["claude-cli"]
    elif prov == "gemini-web":
        return FALLBACK_MODELS["gemini-web"]
    else:
        return []

    if not api_key:
        return FALLBACK_MODELS.get(prov_key, [])

    try:
        if prov_key == "gemini":
            models = await asyncio.to_thread(_fetch_gemini_models_sync, api_key)
        elif prov_key == "claude-api":
            models = await asyncio.to_thread(_fetch_claude_models_sync, api_key)
        elif prov_key == "openai":
            models = await asyncio.to_thread(_fetch_openai_models_sync, api_key, base_url)
        else:
            models = []

        if models:
            return models
    except Exception as exc:
        logger.warning("Failed to discover models for %s: %s", prov_key, exc)

    return FALLBACK_MODELS.get(prov_key, [])
