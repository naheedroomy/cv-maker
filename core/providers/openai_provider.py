# src/cv_maker/providers/openai_provider.py
# OpenAIProvider — OpenAI-compatible API via official openai SDK.
# Supports any OpenAI-compatible endpoint (OpenAI, Groq, Together AI, Ollama, etc.)
# via OPENAI_BASE_URL override.
# Lazy instantiation: OPENAI_API_KEY is read in __init__, never at module scope.
from __future__ import annotations

import logging

import openai

from core.models import BaseCV, GapItem, TailoredCV
from core.pipeline import (
    _build_system_prompt_for_chat,
    _build_user_prompt,
    _extract_json,
    _retry_feedback,
    run_pipeline_staged,
)
from core.providers.base import BaseProvider
from core.validation import check_tailored_cv

logger = logging.getLogger(__name__)

_STAGED_SYSTEM_PROMPT = (
    "You are a precise CV engineering assistant. Return ONLY valid JSON, no commentary."
)


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str = "", model: str = "", base_url: str | None = None) -> None:
        if not api_key:
            raise RuntimeError("OpenAI-compatible API key not configured (set in Settings or .env as OPENAI_API_KEY)")
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model or "gpt-4o-mini"
        # Structured JSON output — disabled automatically if the endpoint rejects
        # response_format (some OpenAI-compatible servers don't support it).
        self._supports_json_mode = True

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        """Single chat completion with JSON mode when the endpoint supports it."""
        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self._supports_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self._client.chat.completions.create(**kwargs)
        except openai.BadRequestError as exc:
            if self._supports_json_mode and "response_format" in str(exc):
                logger.warning(
                    "Endpoint rejected response_format; disabling JSON mode: %s", exc
                )
                self._supports_json_mode = False
                kwargs.pop("response_format", None)
                response = self._client.chat.completions.create(**kwargs)
            else:
                raise
        return response.choices[0].message.content or ""

    def run(self, base_cv: BaseCV, job_text: str, creativity_level: int = 2, user_notes: str = "") -> tuple[TailoredCV, list[GapItem]]:
        system_prompt = _build_system_prompt_for_chat(creativity_level)
        user_prompt = _build_user_prompt(base_cv, job_text, user_notes)
        last_exc: Exception | None = None
        for attempt in range(3):
            logger.info("OpenAI attempt %d/3 for TailoredCV", attempt + 1)
            effective_user = user_prompt
            if attempt > 0:
                logger.warning("Retrying — previous attempt failed: %s", last_exc)
                effective_user = user_prompt + _retry_feedback(last_exc)
            try:
                text = self._chat(system_prompt, effective_user)
                data = _extract_json(text)
                result = TailoredCV.model_validate(data)
                check_tailored_cv(base_cv, result)
                logger.info("OpenAI JSON parse + validation succeeded")
                return result, result.gap_diff
            except (openai.APIError, Exception) as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("OpenAI attempt %d failed: %s", attempt + 1, exc)
        raise RuntimeError(
            f"OpenAI failed to return valid TailoredCV after 3 attempts. Last: {last_exc}"
        )

    def run_staged(
        self, base_cv: BaseCV, job_text: str, creativity_level: int = 2, user_notes: str = ""
    ) -> tuple[TailoredCV, list[GapItem]]:
        """Multi-stage pipeline (requirements → evidence map → generation)."""

        def _call(prompt: str) -> str:
            return self._chat(_STAGED_SYSTEM_PROMPT, prompt)

        return run_pipeline_staged(
            base_cv, job_text, _call,
            creativity_level=creativity_level, user_notes=user_notes,
        )
