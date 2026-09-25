# src/cv_maker/providers/openai_provider.py
# OpenAIProvider — OpenAI-compatible API via official openai SDK.
# Supports any OpenAI-compatible endpoint (OpenAI, Groq, Together AI, Ollama, etc.)
# via OPENAI_BASE_URL override.
# Lazy instantiation: OPENAI_API_KEY is read in __init__, never at module scope.
from __future__ import annotations

import logging
import re

import openai

from core.models import BaseCV, GapItem, TailoredCV
from core.pipeline import _build_system_prompt_for_chat, _build_user_prompt, _extract_json
from core.providers.base import BaseProvider
from core.validation import check_tailored_cv

logger = logging.getLogger(__name__)


def _is_openai_reasoning_model(model_name: str) -> bool:
    mid = model_name.lower()
    return bool(
        mid.startswith("o1")
        or mid.startswith("o3")
        or mid.startswith("o4")
        or re.match(r"^gpt-[5-9]", mid)
    )


class OpenAIProvider(BaseProvider):
    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str | None = None,
        reasoning_effort: str = "auto",
    ) -> None:
        if not api_key:
            raise RuntimeError(
                "OpenAI-compatible API key not configured "
                "(set in Settings or .env as OPENAI_API_KEY)"
            )
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model or "gpt-4o-mini"
        self._reasoning_effort = reasoning_effort or "auto"

    def run(
        self,
        base_cv: BaseCV,
        job_text: str,
        creativity_level: int = 2,
        user_notes: str = "",
    ) -> tuple[TailoredCV, list[GapItem]]:
        system_prompt = _build_system_prompt_for_chat(creativity_level)
        user_prompt = _build_user_prompt(base_cv, job_text, user_notes)
        last_exc: Exception | None = None

        req_kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        if _is_openai_reasoning_model(self._model):
            effort = self._reasoning_effort.lower()
            if effort == "off":
                req_kwargs["reasoning_effort"] = "none"
            elif effort in ("low", "medium", "high"):
                req_kwargs["reasoning_effort"] = effort

        for attempt in range(3):
            logger.info(
                "OpenAI attempt %d/3 for TailoredCV (model=%s, reasoning=%s)",
                attempt + 1,
                self._model,
                self._reasoning_effort,
            )
            effective_user = user_prompt
            if attempt > 0:
                logger.warning("Retrying — previous attempt failed: %s", last_exc)
                effective_user = (
                    user_prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
                )
            req_kwargs["messages"][1]["content"] = effective_user
            try:
                response = self._client.chat.completions.create(**req_kwargs)
                text = response.choices[0].message.content
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
