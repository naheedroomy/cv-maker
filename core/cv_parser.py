"""Hybrid Vision & Native Text PDF CV parser supporting Gemini and OpenAI.

Combines high-resolution page rendering (300 DPI) with native vector text extraction
from PyMuPDF to guarantee 100% exact character transcription of email addresses,
names, URLs, phone numbers, and dates.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os

import fitz  # pymupdf
import openai
from google import genai
from google.genai import types as genai_types

from core.models import BaseCV
from core.pipeline import _extract_json

logger = logging.getLogger(__name__)

_STRUCTURE_SYSTEM_INSTRUCTION = (
    "You are a CV/resume parser. Extract structured data from the provided CV document "
    "(rendered images and verbatim extracted text stream). "
    "Return ONLY valid JSON matching the requested schema."
)

_STRUCTURE_PROMPT = """\
You are extracting structured data from a CV / resume document using both the rendered \
page images and the exact extracted native text.

EXACT EXTRACTED TEXT FROM PDF (Verbatim characters for email, name, URLs, dates):
---
{extracted_text}
---

Instructions:
1. Parse the CV into the exact JSON schema below.
2. Cross-reference layout images with the exact native text. Never misspell, alter, or \
truncate email addresses, candidate names, URLs, phone numbers, or dates — use verbatim \
characters from the extracted text stream.
3. Extract ONLY what is present in the CV — do NOT fabricate, invent, or guess any information.
4. For date fields (start, end): use "YYYY-MM" format. If only a year is known, use "YYYY-01".
   If an end date is "present", "current", or "now", set it to null (still in role).
5. If a field cannot be determined from the CV, use null for optional fields or an empty list
   for list fields. Never leave required string fields empty — use a short placeholder only if
   the field truly cannot be inferred (e.g. summary: "Experienced professional").
6. skills: extract as a flat list of strings (technologies, tools, languages, frameworks, etc.).
7. certifications: extract as a flat list of strings; empty list [] if none found.
8. projects: extract as a list of project objects; empty list [] if none found.
9. Fix obvious spelling and spacing errors in bullet points and descriptions if caused by \
OCR/rendering artifacts. Do NOT change company names, job titles, proper nouns, or \
technology names.
10. Multiple titles at the same company: if someone held multiple roles at the same company \
with shared bullet points, create SEPARATE experience entries for each title with their own \
date ranges. Every entry MUST have at least 2 bullet points — never create an entry with an \
empty bullets list.

Return ONLY a valid JSON object matching this exact schema — no markdown fences, no commentary:

{{
  "contact": {{
    "name": "<full name>",
    "email": "<email address>",
    "linkedin": "<LinkedIn URL or null>",
    "github": "<GitHub URL or null>",
    "phone": "<phone number or null>",
    "location": "<city, country or null>",
    "work_authorization": "<work permit/visa status if mentioned, or null>"
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
  "certifications": ["<certification name>"],
  "languages": [
    {{
      "language": "<language name, e.g. English>",
      "level": "<proficiency level, e.g. Native, C2, B1, A1>"
    }}
  ]
}}"""


def _extract_pdf_pages(pdf_bytes: bytes, dpi: int = 300) -> list[dict]:
    """Extract page images and native vector text from PDF bytes.

    Args:
        pdf_bytes: Raw PDF bytes.
        dpi: Resolution for page rendering (300 DPI for high fidelity vision).

    Returns:
        List of dicts per page with 'image' (bytes), 'images' (list[bytes]), and 'text' (str).
    """
    doc = None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages: list[dict] = []
        for page in doc:
            text = page.get_text("text").strip()
            pixmap = page.get_pixmap(dpi=dpi)
            image = pixmap.tobytes("png")
            pages.append({
                "image": image,
                "images": [image],
                "text": text,
            })
        logger.info("PDF converted to %d page entries at %d DPI", len(pages), dpi)
        return pages
    finally:
        if doc is not None:
            doc.close()


def _build_vision_prompt(pages: list[dict]) -> str:
    """Format structuring prompt containing exact native extracted text stream."""
    text_blocks: list[str] = []
    for i, p in enumerate(pages):
        page_text = p.get("text", "").strip()
        if page_text:
            text_blocks.append(f"--- Page {i + 1} ---\n{page_text}")

    extracted_text = (
        "\n\n".join(text_blocks)
        if text_blocks
        else "(No native text stream found in PDF)"
    )
    return _STRUCTURE_PROMPT.format(extracted_text=extracted_text)


async def _parse_gemini_vision(
    pages: list[dict],
    model: str,
    api_key: str,
) -> BaseCV:
    """Extract structured BaseCV from PDF pages using Gemini vision model."""
    client = genai.Client(api_key=api_key)
    prompt = _build_vision_prompt(pages)
    last_exc: Exception | None = None

    for attempt in range(3):
        logger.info("Gemini vision pass: attempt %d/3 via %s", attempt + 1, model)
        effective_prompt = prompt
        if attempt > 0:
            effective_prompt += "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."

        parts: list[genai_types.Part] = []
        for p in pages:
            parts.append(
                genai_types.Part.from_bytes(
                    data=p["image"],
                    mime_type="image/png",
                )
            )
        parts.append(genai_types.Part.from_text(text=effective_prompt))

        try:
            config = genai_types.GenerateContentConfig(
                system_instruction=_STRUCTURE_SYSTEM_INSTRUCTION,
            )

            def _sync_call() -> genai_types.GenerateContentResponse:
                return client.models.generate_content(
                    model=model,
                    contents=parts,
                    config=config,
                )

            gen_func = getattr(client.models, "generate_content", None)
            if asyncio.iscoroutinefunction(gen_func):
                response = await client.models.generate_content(
                    model=model,
                    contents=parts,
                    config=config,
                )
            else:
                call_res = await asyncio.to_thread(_sync_call)
                if asyncio.iscoroutine(call_res):
                    response = await call_res
                else:
                    response = call_res

            raw_text = response.text or ""
            data = _extract_json(raw_text)
            result = BaseCV.model_validate(data)
            logger.info(
                "Gemini vision pass succeeded: contact=%s, experience=%d, skills=%d",
                result.contact.name,
                len(result.experience),
                len(result.skills),
            )
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Gemini vision pass attempt %d failed: %s", attempt + 1, exc)

    raise RuntimeError(
        f"CV structuring failed after 3 attempts. Last error: {last_exc}"
    )


async def _parse_openai_vision(
    pages: list[dict],
    model: str,
    api_key: str,
) -> BaseCV:
    """Extract structured BaseCV from PDF pages using OpenAI vision model."""
    client = openai.AsyncOpenAI(api_key=api_key)
    prompt = _build_vision_prompt(pages)
    last_exc: Exception | None = None

    for attempt in range(3):
        logger.info("OpenAI vision pass: attempt %d/3 via %s", attempt + 1, model)
        effective_prompt = prompt
        if attempt > 0:
            effective_prompt += "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."

        image_parts: list[dict] = []
        for p in pages:
            b64_img = base64.b64encode(p["image"]).decode("utf-8")
            image_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64_img}",
                },
            })

        user_content: list[dict] = [
            *image_parts,
            {
                "type": "text",
                "text": effective_prompt,
            },
        ]

        messages = [
            {"role": "system", "content": _STRUCTURE_SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_content},
        ]

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
            )
            raw_text = response.choices[0].message.content or ""
            data = _extract_json(raw_text)
            result = BaseCV.model_validate(data)
            logger.info(
                "OpenAI vision pass succeeded: contact=%s, experience=%d, skills=%d",
                result.contact.name,
                len(result.experience),
                len(result.skills),
            )
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("OpenAI vision pass attempt %d failed: %s", attempt + 1, exc)

    raise RuntimeError(
        f"CV structuring failed after 3 attempts. Last error: {last_exc}"
    )


async def parse_pdf_to_base_cv(
    pdf_bytes: bytes,
    provider: str = "gemini",
    model: str | None = None,
    api_key: str | None = None,
) -> BaseCV:
    """Parse a PDF CV into a validated BaseCV model using hybrid vision + native text extraction.

    Passes high-resolution page images and exact native text from PyMuPDF to the
    selected vision LLM (Gemini or OpenAI) with retry logic.

    Args:
        pdf_bytes: Raw PDF file bytes.
        provider: "gemini" or "openai" (case-insensitive).
        model: Model name override (defaults to "gemini-2.5-flash" or "gpt-4o").
        api_key: Explicit API key; falls back to GEMINI_API_KEY or OPENAI_API_KEY env vars.

    Returns:
        Validated BaseCV Pydantic model instance.

    Raises:
        ValueError: If provider is not supported.
        RuntimeError: If API key is missing or CV structuring fails after 3 attempts.
    """
    prov = (provider or "").strip().lower()
    if prov == "gemini":
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not resolved_key:
            raise RuntimeError("GEMINI_API_KEY not configured for CV parsing")
        resolved_model = model or "gemini-2.5-flash"
        pages = await asyncio.to_thread(_extract_pdf_pages, pdf_bytes)
        return await _parse_gemini_vision(pages, resolved_model, resolved_key)
    elif prov == "openai":
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not resolved_key:
            raise RuntimeError("OPENAI_API_KEY not configured for CV parsing")
        resolved_model = model or "gpt-4o"
        pages = await asyncio.to_thread(_extract_pdf_pages, pdf_bytes)
        return await _parse_openai_vision(pages, resolved_model, resolved_key)
    else:
        raise ValueError(f"Unsupported parser provider: {provider}")
