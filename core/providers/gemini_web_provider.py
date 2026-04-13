# core/providers/gemini_web_provider.py
# GeminiWebProvider -- Gemini web app access via gemini-webapi (browser cookies).
# Uses asyncio.run() inside sync run() method. This works because pipeline_runner.py
# dispatches via asyncio.to_thread(), running in a thread pool thread where no event loop exists.
from __future__ import annotations

import asyncio
import logging

from gemini_webapi import GeminiClient
from gemini_webapi.exceptions import AuthError, APIError

from core.models import BaseCV, GapItem, TailoredCV
from core.pipeline import _build_system_prompt_for_chat, _build_user_prompt, _extract_json
from core.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class GeminiWebProvider(BaseProvider):
    DEFAULT_MODEL = "gemini-3-flash"

    def __init__(self, psid: str = "", psidts: str = "", model: str = "") -> None:
        if not psid:
            raise RuntimeError(
                "Gemini Web cookie not configured "
                "(set __Secure-1PSID in Settings or .env as GEMINI_WEB_PSID)"
            )
        self._psid = psid
        self._psidts = psidts
        self._model = model or self.DEFAULT_MODEL

    def run(
        self, base_cv: BaseCV, job_text: str, creativity_level: int = 2
    ) -> tuple[TailoredCV, list[GapItem]]:
        """Sync entry point -- creates a fresh event loop in the thread pool thread."""
        return asyncio.run(self._run_async(base_cv, job_text, creativity_level))

    async def _run_async(
        self, base_cv: BaseCV, job_text: str, creativity_level: int
    ) -> tuple[TailoredCV, list[GapItem]]:
        client = GeminiClient(self._psid, self._psidts)
        await client.init(timeout=30, auto_close=True, close_delay=60, auto_refresh=True)
        try:
            system_prompt = _build_system_prompt_for_chat(creativity_level)
            user_prompt = _build_user_prompt(base_cv, job_text)
            last_exc: Exception | None = None

            for attempt in range(3):
                logger.info("GeminiWeb attempt %d/3 for TailoredCV", attempt + 1)
                effective_user = user_prompt
                if attempt > 0:
                    logger.warning("Retrying -- previous attempt failed: %s", last_exc)
                    effective_user = (
                        user_prompt
                        + "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
                    )

                try:
                    # gemini-webapi has no separate system prompt parameter --
                    # concatenate system + user into a single prompt string
                    full_prompt = f"{system_prompt}\n\n{effective_user}"
                    # Use streaming to avoid response truncation on large CV outputs
                    # (generate_content truncates at ~16k UTF-16 units for large prompts)
                    chunks: list[str] = []
                    async for chunk in client.generate_content_stream(
                        full_prompt, model=self._model
                    ):
                        chunks.append(chunk.text_delta)
                    raw_text = "".join(chunks)
                    data = _extract_json(raw_text)
                    result = TailoredCV.model_validate(data)
                    logger.info("GeminiWeb JSON parse + validation succeeded")
                    return result, result.gap_diff
                except (AuthError, APIError, Exception) as exc:  # noqa: BLE001
                    last_exc = exc
                    logger.warning("GeminiWeb attempt %d failed: %s", attempt + 1, exc)

            raise RuntimeError(
                f"GeminiWeb failed to return valid TailoredCV after 3 attempts. "
                f"Last: {last_exc}"
            )
        finally:
            await client.close()
