# src/cv_maker/pipeline.py
# Claude Code CLI pipeline: BaseCV + job listing -> TailoredCV + gap diff.
# Two sequential claude -p invocations with JSON parse-retry (AI-07).
from __future__ import annotations

import json
import logging
import re
import subprocess
import time

import yaml

logger = logging.getLogger(__name__)

from cv_maker.models import BaseCV, GapItem, TailoredCV

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _invoke_claude(prompt: str, timeout: int = 300) -> str:
    """Invoke claude -p and return raw stdout. Raises RuntimeError on failure."""
    logger.info("Claude CLI: invoking (timeout=%ds, prompt=%d chars)", timeout, len(prompt))
    t0 = time.monotonic()
    try:
        result = subprocess.run(  # noqa: S603
            ["claude", "-p", "--model", "haiku", "--no-session-persistence"],  # noqa: S607
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("Claude CLI: timed out after %ds", timeout)
        raise RuntimeError(
            f"claude -p timed out after {timeout}s — prompt may be too large"
        ) from exc
    elapsed = time.monotonic() - t0
    if result.returncode != 0:
        logger.error("Claude CLI: failed (exit %d) after %.1fs", result.returncode, elapsed)
        raise RuntimeError(
            f"claude -p failed (exit {result.returncode}): {result.stderr[:500]}"
        )
    logger.info("Claude CLI: completed in %.1fs (response=%d chars)", elapsed, len(result.stdout))
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
        logger.info("Attempt %d/%d for %s", attempt + 1, max_attempts, schema_cls.__name__)
        effective_prompt = prompt
        if attempt > 0:
            logger.warning("Retrying — previous attempt failed: %s", last_exc)
            effective_prompt = (
                prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
            )
        try:
            raw = _invoke_claude(effective_prompt)
            data = _extract_json(raw)
            result = schema_cls.model_validate(data)
            logger.info("JSON parse + validation succeeded for %s", schema_cls.__name__)
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Attempt %d failed: %s", attempt + 1, exc)
    raise RuntimeError(
        f"claude -p failed to return valid {schema_cls.__name__} after "
        f"{max_attempts} attempts. Last error: {last_exc}"
    )


def _serialize_base_cv(cv: BaseCV) -> str:
    """Serialize BaseCV to YAML for embedding in prompts."""
    return yaml.dump(cv.model_dump(), default_flow_style=False, allow_unicode=True)


# ---------------------------------------------------------------------------
# Public entry point — single combined Claude call
# ---------------------------------------------------------------------------


def run_pipeline(base_cv: BaseCV, job_text: str) -> tuple[TailoredCV, list[GapItem]]:
    """Full AI pipeline: analyze job + tailor CV in a single Claude call.

    Returns:
        (tailored_cv, gap_diff) where gap_diff is extracted from the combined response.
    """
    base_cv_yaml = _serialize_base_cv(base_cv)
    prompt = f"""\
You are a CV tailoring expert. Given a candidate's base CV and a job listing, you will:
1. Analyze the job requirements and compute a gap diff
2. Produce a tailored CV optimized for the role

BASE CV (YAML format — the candidate's complete experience):
---
{base_cv_yaml}
---

JOB LISTING:
---
{job_text}
---

Instructions:

GAP ANALYSIS:
- Extract key requirements and technologies from the job listing.
- For each requirement, check whether the base CV provides evidence. Include this as "gap_diff" in the output.

CV TAILORING — address each section:
1. SUMMARY: Rewrite to emphasize the experience most relevant to this role. \
Only mention certifications the candidate already holds. Do NOT mention expected/upcoming/in-progress certifications in the summary.
2. EXPERIENCE:
   - Keep entries in reverse chronological order (most recent first). Do NOT reorder by relevance.
   - Rewrite bullets to sound natural and professional. Do NOT write bullets that read like they were \
written specifically to match a job listing. They should sound like real accomplishments, not keyword-stuffed responses.
   - You are NOT limited to the same number of bullets as the base CV. Add additional bullets where \
relevant to highlight experience that aligns with the job requirements. For highly relevant roles, \
5-7 bullets is fine. For less relevant roles, 2-3 is enough. Use your judgement.
   - **BOLD key technologies and tools** in each bullet by wrapping them in **double asterisks**. \
For example: "Built a CI/CD pipeline using **AWS CodePipeline** and **CodeBuild**, reducing deployment time by 50%."
   - You MAY adjust job titles slightly to better align with the target role. For example, \
if the base CV says "Software Engineer" but the job listing is for a DevOps role, you can adjust \
to "Software & DevOps Engineer" or similar — keep it honest but optimize for relevance.
   - If the job listing requires technologies the candidate hasn't explicitly listed, you MAY \
weave them naturally into existing bullet points as supplementary mentions, or add a small new \
bullet point that lightly claims familiarity. Keep additions inside the experience bullets. \
For example, if they use Kubernetes heavily, mentioning Helm in a bullet is fine.
   - Avoid overusing em dashes (—). Use commas, periods, or semicolons for variety. One or two em dashes \
across the entire CV is fine, but they should not appear in every bullet.
3. SKILLS: Filter and reorder skills to lead with those most relevant to this role. \
If you added a technology in the experience bullets above, you may also list it here — but the \
primary home for added tech is in the bullet points, not standalone in this section.
4. HIGHLIGHTED TECHNOLOGIES: Surface technologies from the base CV that the candidate \
knows but did not lead with. Technologies you wove into experience bullets may also appear here.
5. EDUCATION and PROJECTS and CERTIFICATIONS: Pass through unchanged.
6. CONTACT: Pass through unchanged.
7. TAILORING NOTES: Provide a list of 5-10 notes explaining what you changed and why. Include:
   - Job titles you adjusted and the reasoning
   - Technologies you added that weren't in the base CV and why they're reasonable
   - Key bullet rewrites and what job requirement they target
   - Any strategic decisions (e.g., emphasizing certain experience over others)

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
  "highlighted_technologies": ["<surfaced tech from base CV>"],
  "tailoring_notes": ["<note explaining what you changed and why>"],
  "gap_diff": [
    {{
      "requirement": "<requirement from job listing>",
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
    result = _invoke_with_retry(prompt, TailoredCV)
    return result, result.gap_diff
