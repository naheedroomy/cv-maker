"""Two-pass PDF CV parser: pymupdf page-to-image + Gemini OCR + Gemini structuring.

Decision D-01: Use Gemini 2.5 Flash-Lite for both OCR and structuring passes.
Decision D-01: PDF only — no DOCX handling.
Decision D-01: Use inhouse GEMINI_API_KEY from .env (not per-user key).
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os

import fitz  # pymupdf
from google import genai
from google.genai import types as genai_types

from core.models import BaseCV
from core.pipeline import _extract_json

logger = logging.getLogger(__name__)

_OCR_SYSTEM_INSTRUCTION = (
    "You are an OCR engine. Extract ALL text from this CV/resume image. "
    "Preserve the structure (headings, bullet points, dates, contact info). "
    "Return the extracted text faithfully — do not summarize, rephrase, or omit anything."
)

_STRUCTURE_SYSTEM_INSTRUCTION = (
    "You are a CV/resume parser. Extract structured data from the provided CV text. "
    "Return ONLY valid JSON matching the requested schema."
)

_STRUCTURE_PROMPT = """\
You are extracting structured data from a CV / resume document.

CV TEXT:
---
{ocr_text}
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
company names, job titles, proper nouns, or technology names — only fix clear typos.
9. Multiple titles at the same company: if someone held multiple roles at the same company \
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


def _pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> list[bytes]:
    """Convert each page of a PDF to a PNG byte array.

    Args:
        pdf_bytes: Raw PDF file bytes.
        dpi: Resolution for page rendering (200 DPI is a good balance of quality/size).

    Returns:
        List of PNG byte arrays, one per page.
    """
    doc = None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images: list[bytes] = []
        for page in doc:
            pixmap = page.get_pixmap(dpi=dpi)
            images.append(pixmap.tobytes("png"))
        logger.info("PDF converted to %d page images at %d DPI", len(images), dpi)
        return images
    finally:
        if doc is not None:
            doc.close()


def _ocr_images(images: list[bytes], client: genai.Client, model: str) -> str:
    """Pass 1: Extract text from page images via Gemini OCR.

    Sends all page images in a single request.

    Args:
        images: List of PNG byte arrays (one per page).
        client: Initialized Gemini client.
        model: Gemini model name.

    Returns:
        Extracted text from all pages.
    """
    parts: list[genai_types.Part] = []
    for image_bytes in images:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        parts.append(
            genai_types.Part.from_bytes(
                data=base64.b64decode(encoded),
                mime_type="image/png",
            )
        )
    logger.info("OCR pass: sending %d page images to Gemini (%s)", len(parts), model)
    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=genai_types.GenerateContentConfig(
            system_instruction=_OCR_SYSTEM_INSTRUCTION,
        ),
    )
    ocr_text = response.text or ""
    logger.info("OCR pass: extracted %d chars of text", len(ocr_text))
    return ocr_text


def _structure_text(ocr_text: str, client: genai.Client, model: str) -> BaseCV:
    """Pass 2: Convert OCR text into a validated BaseCV using Gemini.

    Retries up to 3 times on parse/validation failure.

    Args:
        ocr_text: Raw text extracted from the CV in Pass 1.
        client: Initialized Gemini client.
        model: Gemini model name.

    Returns:
        Validated BaseCV instance.

    Raises:
        RuntimeError: If structuring fails after 3 attempts.
    """
    user_prompt = _STRUCTURE_PROMPT.format(ocr_text=ocr_text)
    last_exc: Exception | None = None

    for attempt in range(3):
        logger.info("Structuring pass: attempt %d/3 via %s", attempt + 1, model)
        effective_prompt = user_prompt
        if attempt > 0:
            effective_prompt += "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."

        try:
            response = client.models.generate_content(
                model=model,
                contents=effective_prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=_STRUCTURE_SYSTEM_INSTRUCTION,
                ),
            )
            raw_text = response.text or ""
            data = _extract_json(raw_text)
            result = BaseCV.model_validate(data)
            logger.info(
                "Structuring pass: succeeded — contact=%s, experience=%d, skills=%d",
                result.contact.name,
                len(result.experience),
                len(result.skills),
            )
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Structuring pass attempt %d failed: %s", attempt + 1, exc)

    raise RuntimeError(
        f"CV structuring failed after 3 attempts. Last error: {last_exc}"
    )


async def parse_pdf_to_base_cv(pdf_bytes: bytes) -> BaseCV:
    """Parse a PDF CV into a validated BaseCV model using a two-pass Gemini pipeline.

    Pass 1 (OCR): pymupdf converts pages to PNG images, Gemini extracts text.
    Pass 2 (Structuring): Gemini converts OCR text to structured BaseCV JSON.

    Uses the inhouse GEMINI_API_KEY from the environment (not per-user key).

    Args:
        pdf_bytes: Raw PDF file bytes.

    Returns:
        Validated BaseCV Pydantic model instance.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not configured or parsing fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured for CV parsing")

    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-flash-lite"

    # All three sync steps wrapped in asyncio.to_thread since they do I/O
    images = await asyncio.to_thread(_pdf_to_images, pdf_bytes)
    ocr_text = await asyncio.to_thread(_ocr_images, images, client, model)
    result = await asyncio.to_thread(_structure_text, ocr_text, client, model)

    return result
