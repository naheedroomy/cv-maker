# src/cv_maker/providers/gemini_provider.py
# GeminiProvider — Gemini 2.5 Flash via google-genai SDK.
# Lazy instantiation: GEMINI_API_KEY is read in __init__, never at module scope.
from __future__ import annotations

import logging
import os

from google import genai
from google.genai import errors as genai_errors

from cv_maker.models import BaseCV, GapItem, TailoredCV
from cv_maker.pipeline import _build_prompt, _extract_json
from cv_maker.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    MODEL_ID = "gemini-2.5-flash"

    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        self._client = genai.Client(api_key=api_key)

    def run(self, base_cv: BaseCV, job_text: str) -> tuple[TailoredCV, list[GapItem]]:
        prompt = _build_prompt(base_cv, job_text)
        last_exc: Exception | None = None
        for attempt in range(3):
            logger.info("Gemini attempt %d/3 for TailoredCV", attempt + 1)
            effective_prompt = prompt
            if attempt > 0:
                logger.warning("Retrying — previous attempt failed: %s", last_exc)
                effective_prompt = (
                    prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
                )
            try:
                response = self._client.models.generate_content(
                    model=self.MODEL_ID,
                    contents=effective_prompt,
                )
                data = _extract_json(response.text)
                result = TailoredCV.model_validate(data)
                logger.info("Gemini JSON parse + validation succeeded")
                return result, result.gap_diff
            except (genai_errors.APIError, Exception) as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("Gemini attempt %d failed: %s", attempt + 1, exc)
        raise RuntimeError(
            f"Gemini failed to return valid TailoredCV after 3 attempts. Last: {last_exc}"
        )
