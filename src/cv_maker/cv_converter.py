# src/cv_maker/cv_converter.py
# CV-to-YAML converter: parses an existing CV (plain text) into a BaseCV Pydantic model
# using Claude Code CLI, then saves it as base_cv.yaml.
from __future__ import annotations

from pathlib import Path

import yaml

from cv_maker.data import DEFAULT_CV_PATH
from cv_maker.models import BaseCV
from cv_maker.pipeline import _invoke_with_retry


def convert_cv_to_yaml(cv_text: str) -> BaseCV:
    """Parse plain-text CV content into a validated BaseCV instance using Claude CLI.

    Sends the CV text to Claude Code CLI with an explicit schema prompt. Retries up to 3
    times via _invoke_with_retry. Raises RuntimeError if all attempts fail.

    Args:
        cv_text: Raw CV text (pasted from a PDF viewer or read from a .txt file).

    Returns:
        A validated BaseCV Pydantic model instance.
    """
    prompt = f"""\
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
    return _invoke_with_retry(prompt, BaseCV, max_attempts=3)


def save_base_cv(cv: BaseCV, path: Path | None = None) -> Path:
    """Serialize a BaseCV instance to YAML and write it to disk.

    Defaults to DEFAULT_CV_PATH (base_cv.yaml in the working directory) matching data.py.

    Args:
        cv: Validated BaseCV instance to save.
        path: Optional override path. Defaults to DEFAULT_CV_PATH.

    Returns:
        The Path where the file was written.
    """
    if path is None:
        path = DEFAULT_CV_PATH

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cv.model_dump(), f, default_flow_style=False, allow_unicode=True)

    return path
