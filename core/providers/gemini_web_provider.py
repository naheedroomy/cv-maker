# core/providers/gemini_web_provider.py
# GeminiWebProvider -- Gemini web app access via gemini-webapi (browser cookies).
# Uses asyncio.run() inside sync run() method. This works because pipeline_runner.py
# dispatches via asyncio.to_thread(), running in a thread pool thread where no event loop exists.
from __future__ import annotations

import asyncio
import logging
import re

from gemini_webapi import GeminiClient
from gemini_webapi.exceptions import AuthError, APIError

from core.models import BaseCV, GapItem, TailoredCV
from core.pipeline import _build_system_prompt_for_chat, _build_user_prompt, _extract_json
from core.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# Silence noisy frame-parsing debug spam from gemini-webapi internals
logging.getLogger("gemini_webapi.utils.parsing").setLevel(logging.WARNING)


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

    @staticmethod
    def _sanitize_gemini_output(text: str) -> str:
        """Fix Gemini web app quirks that produce invalid JSON.

        1. Strip markdown code fences (```json ... ```)
        2. Unescape markdown underscore escaping: ``\\_`` -> ``_``
        3. Unwrap Google Search markdown links: ``[text](url)`` -> ``text``
        4. Extract outermost JSON object if wrapped in non-JSON text
        """
        # Strip markdown code fences
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```", "", text)
        # Remove ALL invalid JSON backslash escapes from Gemini's markdown formatting.
        # JSON only allows: \" \\ \/ \b \f \n \r \t \uXXXX
        # Gemini outputs markdown escapes like \_ \> \* \# \- \. etc.
        text = re.sub(r'\\([^"\\/bfnrtu])', r'\1', text)
        # Unwrap markdown links that Gemini wraps around URLs
        text = re.sub(r"\[([^\]]+)\]\(https?://[^\)]+\)", r"\1", text)
        # Extract the outermost JSON object by brace matching
        start = text.find("{")
        if start != -1:
            depth = 0
            in_string = False
            escape_next = False
            for i, ch in enumerate(text[start:], start):
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\":
                    escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        text = text[start : i + 1]
                        break
        return text.strip()

    def run(
        self, base_cv: BaseCV, job_text: str, creativity_level: int = 2
    ) -> tuple[TailoredCV, list[GapItem]]:
        """Sync entry point -- creates a fresh event loop in the thread pool thread."""
        return asyncio.run(self._run_async(base_cv, job_text, creativity_level))

    async def _run_async(
        self, base_cv: BaseCV, job_text: str, creativity_level: int
    ) -> tuple[TailoredCV, list[GapItem]]:
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

            # Fresh client per attempt — stream suspension corrupts client state
            client = GeminiClient(self._psid, self._psidts)
            await client.init(timeout=30, auto_close=True, close_delay=60, auto_refresh=True)
            try:
                # gemini-webapi has no separate system prompt parameter --
                # concatenate system + user into a single prompt string
                full_prompt = f"{system_prompt}\n\n{effective_user}"
                response = await client.generate_content(
                    full_prompt, model=self._model
                )
                logger.info(
                    "GeminiWeb raw response: %d chars, starts=%r, ends=%r",
                    len(response.text),
                    response.text[:80],
                    response.text[-80:],
                )
                raw_text = self._sanitize_gemini_output(response.text)
                data = _extract_json(raw_text)
                result = TailoredCV.model_validate(data)
                logger.info("GeminiWeb JSON parse + validation succeeded")
                return result, result.gap_diff
            except (AuthError, APIError, Exception) as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("GeminiWeb attempt %d failed: %s", attempt + 1, exc)
            finally:
                await client.close()

        raise RuntimeError(
            f"GeminiWeb failed to return valid TailoredCV after 3 attempts. "
            f"Last: {last_exc}"
        )
