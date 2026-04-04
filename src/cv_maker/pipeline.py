# src/cv_maker/pipeline.py
# Claude Code CLI pipeline: BaseCV + job listing -> TailoredCV + gap diff.
# Two sequential claude -p invocations with JSON parse-retry (AI-07).
from __future__ import annotations

import json
import re
import subprocess

import yaml

from cv_maker.models import BaseCV, GapItem, JobAnalysis, TailoredCV

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _invoke_claude(prompt: str, timeout: int = 120) -> str:
    """Invoke claude -p and return raw stdout. Raises RuntimeError on failure."""
    try:
        result = subprocess.run(  # noqa: S603
            ["claude", "-p", "--no-session-persistence", prompt],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"claude -p timed out after {timeout}s — prompt may be too large"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"claude -p failed (exit {result.returncode}): {result.stderr[:500]}"
        )
    return result.stdout


def _extract_json(text: str) -> dict:
    """Extract JSON from claude stdout, stripping markdown fences if present."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    raise ValueError(f"No JSON object found in claude output: {text[:300]!r}")


def _invoke_with_retry(prompt: str, schema_cls, max_attempts: int = 3):
    """Invoke claude -p with JSON parse-retry. Returns validated Pydantic model instance."""
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        effective_prompt = prompt
        if attempt > 0:
            effective_prompt = (
                prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
            )
        try:
            raw = _invoke_claude(effective_prompt)
            data = _extract_json(raw)
            return schema_cls.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise RuntimeError(
        f"claude -p failed to return valid {schema_cls.__name__} after "
        f"{max_attempts} attempts. Last error: {last_exc}"
    )


def _serialize_base_cv(cv: BaseCV) -> str:
    """Serialize BaseCV to YAML for embedding in prompts."""
    return yaml.dump(cv.model_dump(), default_flow_style=False, allow_unicode=True)


# ---------------------------------------------------------------------------
# Public API: Step 1 — Job analysis
# ---------------------------------------------------------------------------


def analyze_job(base_cv: BaseCV, job_text: str) -> JobAnalysis:
    """Step 1: Extract job requirements and compute gap diff using Claude Code CLI.

    AI-01: Extracts structured requirements from job listing.
    DATA-03: Produces gap_diff list for UI display.
    """
    base_cv_yaml = _serialize_base_cv(base_cv)
    prompt = f"""\
You are analyzing a job listing to extract structured requirements and compute a gap diff \
against a candidate's base CV.

BASE CV (YAML format — the candidate's complete experience):
---
{base_cv_yaml}
---

JOB LISTING:
---
{job_text}
---

Instructions:
1. Extract the key requirements and required technologies from the job listing.
2. For each requirement, check whether the base CV provides evidence of this skill or experience.
3. Do NOT fabricate any skills or experience not present in the base CV.
4. Return ONLY a valid JSON object matching this exact schema — no markdown fences, no commentary:

{{
  "role_title": "<inferred job title>",
  "key_requirements": ["<requirement 1>", ...],
  "required_technologies": ["<tech 1>", ...],
  "gap_diff": [
    {{
      "requirement": "<requirement>",
      "present": true,
      "evidence": "<quote or reference from base CV>"
    }},
    {{
      "requirement": "<missing requirement>",
      "present": false,
      "evidence": ""
    }}
  ]
}}"""
    return _invoke_with_retry(prompt, JobAnalysis)


# ---------------------------------------------------------------------------
# Public API: Step 2 — CV tailoring
# ---------------------------------------------------------------------------


def tailor_cv(base_cv: BaseCV, analysis: JobAnalysis) -> TailoredCV:
    """Step 2: Produce tailored CV using job analysis output.

    AI-02: Selects most relevant experience and skills.
    AI-03: Rewrites bullets using job-listing language.
    AI-04: Surfaces highlighted_technologies.
    AI-05: Section-by-section prompting (each section addressed individually).
    AI-06: No-fabrication enforced by including full base CV + explicit instruction.
    LAY-01: Experience and skills reordered by relevance.
    """
    base_cv_yaml = _serialize_base_cv(base_cv)
    requirements_list = "\n".join(f"  - {r}" for r in analysis.key_requirements)
    technologies_list = "\n".join(f"  - {t}" for t in analysis.required_technologies)
    prompt = f"""\
You are tailoring a CV for a specific job listing. Use the base CV as your ONLY source of \
truth — the candidate's complete, unfiltered experience.

BASE CV (YAML format):
---
{base_cv_yaml}
---

JOB REQUIREMENTS (extracted from job listing):
  Role: {analysis.role_title}
  Key requirements:
{requirements_list}
  Required technologies:
{technologies_list}

Instructions — address each CV section independently:
1. SUMMARY: Rewrite to emphasize the experience most relevant to this role.
2. EXPERIENCE: Reorder entries with the most relevant to this role first. \
Rewrite bullets using language from the job listing where appropriate.
3. SKILLS: Filter and reorder skills to lead with those most relevant to this role.
4. HIGHLIGHTED TECHNOLOGIES: Surface technologies from the base CV that the candidate \
knows but did not lead with — add these to highlighted_technologies.
5. EDUCATION and PROJECTS and CERTIFICATIONS: Pass through unchanged.
6. CONTACT: Pass through unchanged.
DO NOT fabricate any experience, skills, credentials, or technologies not present in the base CV.

Return ONLY a valid JSON object matching this exact schema — no markdown fences, no commentary:

{{
  "contact": {{"name": "<str>", "email": "<str>", "linkedin": "<str or null>",
               "github": "<str or null>", "phone": "<str or null>", "location": "<str or null>"}},
  "summary": "<tailored summary>",
  "experience": [
    {{
      "company": "<str>",
      "title": "<str>",
      "start": "<YYYY-MM>",
      "end": "<YYYY-MM or null>",
      "bullets": ["<rewritten bullet>"],
      "technologies": ["<tech>"]
    }}
  ],
  "skills": ["<most relevant first>"],
  "education": [{{"institution": "<str>", "degree": "<str>",
                   "field": "<str or null>", "year": "<int or null>"}}],
  "projects": [{{"name": "<str>", "description": "<str>",
                  "technologies": [], "url": "<str or null>"}}],
  "certifications": ["<str>"],
  "highlighted_technologies": ["<surfaced tech from base CV>"]
}}"""
    return _invoke_with_retry(prompt, TailoredCV)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_pipeline(base_cv: BaseCV, job_text: str) -> tuple[TailoredCV, list[GapItem]]:
    """Full AI pipeline: analyze job then tailor CV.

    Returns:
        (tailored_cv, gap_diff) where gap_diff is the list[GapItem] from step 1.
    """
    analysis = analyze_job(base_cv, job_text)
    tailored = tailor_cv(base_cv, analysis)
    return tailored, analysis.gap_diff
