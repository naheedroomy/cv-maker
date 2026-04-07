# src/cv_maker/providers/openai_provider.py
# OpenAIProvider — OpenAI-compatible API via official openai SDK.
# Supports any OpenAI-compatible endpoint (OpenAI, Groq, Together AI, Ollama, etc.)
# via OPENAI_BASE_URL override.
# Lazy instantiation: OPENAI_API_KEY is read in __init__, never at module scope.
from __future__ import annotations

import logging
import os

import openai

from core.models import BaseCV, GapItem, TailoredCV
from core.pipeline import _build_system_prompt_for_chat, _build_user_prompt, _extract_json
from core.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        from backend.settings_cache import get_setting
        base_url = get_setting("openai_base_url") or None
        self._model = get_setting("openai_model") or "gpt-4o-mini"
        kwargs: dict[str, str] = {"api_key": api_key}
        if base_url is not None:
            kwargs["base_url"] = base_url
        self._client = openai.OpenAI(**kwargs)

    def run(self, base_cv: BaseCV, job_text: str, creativity_level: int = 2) -> tuple[TailoredCV, list[GapItem]]:
        system_prompt = _build_system_prompt_for_chat(creativity_level)
        user_prompt = _build_user_prompt(base_cv, job_text)
        last_exc: Exception | None = None
        for attempt in range(3):
            logger.info("OpenAI attempt %d/3 for TailoredCV", attempt + 1)
            effective_user = user_prompt
            if attempt > 0:
                logger.warning("Retrying — previous attempt failed: %s", last_exc)
                effective_user = (
                    user_prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
                )
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": effective_user},
                    ],
                )
                text = response.choices[0].message.content
                data = _extract_json(text)
                result = TailoredCV.model_validate(data)
                logger.info("OpenAI JSON parse + validation succeeded")
                return result, result.gap_diff
            except (openai.APIError, Exception) as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("OpenAI attempt %d failed: %s", attempt + 1, exc)
        raise RuntimeError(
            f"OpenAI failed to return valid TailoredCV after 3 attempts. Last: {last_exc}"
        )
