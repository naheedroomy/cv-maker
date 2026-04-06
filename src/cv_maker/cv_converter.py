# src/cv_maker/cv_converter.py
# CV-to-YAML converter: parses an existing CV (plain text) into a BaseCV Pydantic model
# using any configured AI provider, then saves it as base_cv.yaml.
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import yaml

from cv_maker.data import DEFAULT_CV_PATH
from cv_maker.models import BaseCV
from cv_maker.pipeline import _extract_json, _invoke_with_retry

logger = logging.getLogger(__name__)

_CONVERT_PROMPT = """\
You are extracting structured data from a CV / resume document.

CV TEXT:
---
{cv_text}
---

Instructions:
1. Parse the CV text above into the exact JSON schema below.
2. Extract ONLY what is present in the CV — do NOT fabricate, invent, or guess any information.
3. For date fields (start, end): use "YYYY-MM" format. If only a year is known, use "YYYY-01".
   If an end date is "present", "current", or "now", set it to null (still in role).
4. If a field cannot be determined from the CV, use null for optional fields or an empty list
   for list fields. Never leave required string fields empty — use a short placeholder only if
   the field truly cannot be inferred (e.g. summary: "Experienced professional").
5. skills: extract as a flat list of strings (technologies, tools, languages, frameworks, etc.).
6. certifications: extract as a flat list of strings; empty list [] if none found.
7. projects: extract as a list of project objects; empty list [] if none found.
8. The pasted CV text may contain typos, OCR artifacts, or formatting issues from copy-paste. \
Fix obvious spelling and spacing errors in bullet points and descriptions. Do NOT change \
company names, job titles, proper nouns, or technology names — only fix clear typos \
(e.g. "mangement" -> "management", extra spaces, broken words).

Return ONLY a valid JSON object matching this exact schema — no markdown fences, no commentary:

{{
  "contact": {{
    "name": "<full name>",
    "email": "<email address>",
    "linkedin": "<LinkedIn URL or null>",
    "github": "<GitHub URL or null>",
    "phone": "<phone number or null>",
    "location": "<city, country or null>"
  }},
  "summary": "<professional summary — extract from CV or infer from overall experience>",
  "experience": [
    {{
      "company": "<company name>",
      "title": "<job title>",
      "location": "<city, country or null if not mentioned>",
      "start": "<YYYY-MM>",
      "end": "<YYYY-MM or null if current>",
      "bullets": ["<responsibility or achievement>"],
      "technologies": ["<technology used in this role>"]
    }}
  ],
  "skills": ["<skill or technology>"],
  "education": [
    {{
      "institution": "<university or school name>",
      "degree": "<degree type, e.g. BSc, MSc, PhD>",
      "field": "<field of study or null>",
      "year": <graduation year as integer or null>
    }}
  ],
  "projects": [
    {{
      "name": "<project name>",
      "description": "<brief description>",
      "technologies": ["<tech used>"],
      "url": "<URL or null>"
    }}
  ],
  "certifications": ["<certification name>"]
}}"""


def convert_cv_to_yaml(cv_text: str, model: str = "claude-haiku") -> BaseCV:
    """Parse plain-text CV content into a validated BaseCV instance.

    Uses the specified provider (defaults to Claude CLI). Falls back to
    Claude CLI for backwards compatibility.

    Args:
        cv_text: Raw CV text (pasted from a PDF viewer or read from a .txt file).
        model: Provider key — "claude-haiku", "claude-api", "gemini-flash", or "openai".

    Returns:
        A validated BaseCV Pydantic model instance.
    """
    prompt = _CONVERT_PROMPT.format(cv_text=cv_text)

    if model == "claude-haiku":
        # Use Claude CLI directly (original behavior)
        return _invoke_with_retry(prompt, BaseCV, max_attempts=3)

    # Use API-based provider
    from cv_maker.providers import get_provider

    provider = get_provider(model)

    # API providers need system/user split
    system_prompt = (
        "You are a CV/resume parser. Extract structured data from the provided CV text. "
        "Return ONLY valid JSON matching the requested schema."
    )
    user_prompt = prompt

    last_exc: Exception | None = None
    for attempt in range(3):
        logger.info("CV convert attempt %d/3 via %s", attempt + 1, type(provider).__name__)
        effective_user = user_prompt
        if attempt > 0:
            effective_user += "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
        try:
            text = _invoke_provider(provider, system_prompt, effective_user)
            data = _extract_json(text)
            result = BaseCV.model_validate(data)
            logger.info("CV convert succeeded via %s", type(provider).__name__)
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("CV convert attempt %d failed: %s", attempt + 1, exc)

    raise RuntimeError(
        f"CV conversion failed after 3 attempts via {type(provider).__name__}. Last: {last_exc}"
    )


def _invoke_provider(provider, system_prompt: str, user_prompt: str) -> str:
    """Invoke an API provider and return raw text response."""
    import anthropic
    import openai as openai_mod
    from google import genai
    from google.genai import types as genai_types

    from cv_maker.providers.claude_api_provider import ClaudeAPIProvider
    from cv_maker.providers.gemini_provider import GeminiProvider
    from cv_maker.providers.openai_provider import OpenAIProvider

    if isinstance(provider, ClaudeAPIProvider):
        response = provider._client.messages.create(
            model=provider._model,
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return next((b.text for b in response.content if b.type == "text"), "")

    if isinstance(provider, GeminiProvider):
        response = provider._client.models.generate_content(
            model=provider._model,
            contents=user_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        return response.text

    if isinstance(provider, OpenAIProvider):
        response = provider._client.chat.completions.create(
            model=provider._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    raise RuntimeError(f"Unsupported provider for CV conversion: {type(provider).__name__}")


def save_base_cv(cv: BaseCV, path: Path | None = None) -> Path:
    """Serialize a BaseCV instance to YAML and write it to disk."""
    if path is None:
        path = DEFAULT_CV_PATH

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cv.model_dump(), f, default_flow_style=False, allow_unicode=True)

    return path
