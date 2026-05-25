# src/cv_maker/providers/gemini_provider.py
# GeminiProvider — Gemini 3.1 Flash-Lite via google-genai SDK.
# Lazy instantiation: GEMINI_API_KEY is read in __init__, never at module scope.
from __future__ import annotations

import logging

from google import genai
from google.genai import errors as genai_errors

from google.genai import types as genai_types

from core.models import BaseCV, GapItem, TailoredCV
from core.pipeline import _build_system_prompt_for_chat, _build_user_prompt, _extract_json
from core.providers.base import BaseProvider
from core.validation import check_tailored_cv

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"

    def __init__(self, api_key: str = "", model: str = "") -> None:
        if not api_key:
            raise RuntimeError("Gemini API key not configured (set in Settings or .env as GEMINI_API_KEY)")
        self._client = genai.Client(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL

    def run(self, base_cv: BaseCV, job_text: str, creativity_level: int = 2, user_notes: str = "") -> tuple[TailoredCV, list[GapItem]]:
        system_prompt = _build_system_prompt_for_chat(creativity_level)
        user_prompt = _build_user_prompt(base_cv, job_text, user_notes)
        last_exc: Exception | None = None
        for attempt in range(3):
            logger.info("Gemini attempt %d/3 for TailoredCV", attempt + 1)
            effective_user = user_prompt
            if attempt > 0:
                logger.warning("Retrying — previous attempt failed: %s", last_exc)
                effective_user = (
                    user_prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
                )
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=effective_user,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    ),
                )
                data = _extract_json(response.text)
                result = TailoredCV.model_validate(data)
                check_tailored_cv(base_cv, result)
                logger.info("Gemini JSON parse + validation succeeded")
                return result, result.gap_diff
            except (genai_errors.APIError, Exception) as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("Gemini attempt %d failed: %s", attempt + 1, exc)
        raise RuntimeError(
            f"Gemini failed to return valid TailoredCV after 3 attempts. Last: {last_exc}"
        )
