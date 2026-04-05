# src/cv_maker/providers/claude_api_provider.py
# ClaudeAPIProvider — Claude via Anthropic SDK (not CLI).
# Lazy instantiation: ANTHROPIC_API_KEY is read in __init__, never at module scope.
from __future__ import annotations

import logging
import os

import anthropic

from cv_maker.models import BaseCV, GapItem, TailoredCV
from cv_maker.pipeline import _build_system_prompt_for_chat, _build_user_prompt, _extract_json
from cv_maker.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class ClaudeAPIProvider(BaseProvider):
    DEFAULT_MODEL = "claude-haiku-4-5"

    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")
        self._model = os.environ.get("CLAUDE_API_MODEL") or self.DEFAULT_MODEL
        self._client = anthropic.Anthropic(api_key=api_key)

    def run(self, base_cv: BaseCV, job_text: str) -> tuple[TailoredCV, list[GapItem]]:
        system_prompt = _build_system_prompt_for_chat()
        user_prompt = _build_user_prompt(base_cv, job_text)
        last_exc: Exception | None = None
        for attempt in range(3):
            logger.info("Claude API attempt %d/3 for TailoredCV (model=%s)", attempt + 1, self._model)
            effective_user = user_prompt
            if attempt > 0:
                logger.warning("Retrying — previous attempt failed: %s", last_exc)
                effective_user = (
                    user_prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
                )
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=16000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": effective_user}],
                )
                text = next(
                    (b.text for b in response.content if b.type == "text"), ""
                )
                data = _extract_json(text)
                result = TailoredCV.model_validate(data)
                logger.info("Claude API JSON parse + validation succeeded")
                return result, result.gap_diff
            except (anthropic.APIError, Exception) as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("Claude API attempt %d failed: %s", attempt + 1, exc)
        raise RuntimeError(
            f"Claude API failed to return valid TailoredCV after 3 attempts. Last: {last_exc}"
        )
