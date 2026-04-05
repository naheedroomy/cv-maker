# src/cv_maker/pipeline.py
# Claude Code CLI pipeline: BaseCV + job listing -> TailoredCV + gap diff.
# Two sequential claude -p invocations with JSON parse-retry (AI-07).
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time

import yaml

logger = logging.getLogger(__name__)

from cv_maker.models import BaseCV, GapItem, TailoredCV

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_claude_cli_model() -> str:
    """Get Claude CLI model from settings cache, env, or default."""
    try:
        from backend.settings_cache import get_setting
        model = get_setting("claude_cli_model")
        if model:
            return model
    except ImportError:
        pass
    return os.environ.get("CLAUDE_MODEL", "haiku")


def _invoke_claude(prompt: str, timeout: int = 300) -> str:
    """Invoke claude -p and return raw stdout. Raises RuntimeError on failure."""
    logger.info("Claude CLI: invoking (timeout=%ds, prompt=%d chars)", timeout, len(prompt))
    t0 = time.monotonic()
    try:
        result = subprocess.run(  # noqa: S603
            ["claude", "-p", "--model", _get_claude_cli_model(), "--no-session-persistence"],  # noqa: S607
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
        else:
            raise ValueError(f"No JSON object found in claude output: {text[:300]!r}")

    # Normalize tailoring_notes: some models return dicts instead of strings
    if "tailoring_notes" in data and isinstance(data["tailoring_notes"], list):
        data["tailoring_notes"] = [
            " ".join(str(v) for v in note.values()) if isinstance(note, dict) else str(note)
            for note in data["tailoring_notes"]
        ]

    return data


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


def _build_system_prompt() -> str:
    """Build the system prompt with instructions and output schema.

    Used by chat-based providers (OpenAI, Gemini) as the system message.
    Claude CLI concatenates this with the user prompt via _build_prompt().
    """
    return """\
You are a CV tailoring expert. Given a candidate's base CV and a job listing, you will:
1. Analyze the job requirements and compute a gap diff
2. Produce a tailored CV optimized for the role

Instructions:

GAP ANALYSIS:
- Extract key requirements and technologies from the job listing.
- For each requirement, evaluate the base CV for evidence. Consider both explicit mentions AND \
implicit signals. For example: observability work implies SRE practices; Kubernetes platform work \
implies Helm, GitOps, or deployment standardization; MTTD/MTTR work implies incident response maturity.
- Assign a match_level for each requirement: "strong" (clear, direct evidence), "partial" \
(related or implicit evidence), or "missing" (no evidence found).
- Include this as "gap_diff" in the output.

CV TAILORING — address each section:
1. SUMMARY: Position the candidate to match the role's core identity (e.g., Platform Engineer, SRE, DevOps). \
Reflect seniority signals such as ownership, system design, and cross-team impact. \
Prioritize the top 3 themes from the job description. \
Only mention certifications the candidate already holds. Do NOT mention expected/upcoming/in-progress certifications in the summary. \
Do NOT use **bold** markers in the summary — bold formatting is only for experience bullets.
2. EXPERIENCE:
   - NEVER change dates (start, end) from the base CV. The dates are correct as provided — even if they \
appear to be in the future. Your training data has a knowledge cutoff; the base CV reflects real-world dates.
   - Keep entries in reverse chronological order (most recent first). Do NOT reorder by relevance.
   - Rewrite bullets to sound natural and professional. Do NOT write bullets that read like they were \
written specifically to match a job listing. They should sound like real accomplishments, not keyword-stuffed responses. \
Avoid directly reusing phrases from the job listing. Prefer paraphrasing into natural, experience-driven language.
   - When rewriting bullets, ensure each claim can be traced back to explicit or implicit evidence \
from the base CV. Do not introduce responsibilities, scope, or technologies that cannot be justified by the base CV.
   - Preserve the level of ownership indicated in the base CV. Do not upgrade action verbs \
(e.g., "worked on" to "led", "contributed to" to "architected") unless clearly supported by the original bullet.
   - You are NOT limited to the same number of bullets as the base CV. Add additional bullets where \
relevant to highlight experience that aligns with the job requirements. For highly relevant roles, \
5-7 bullets is fine. For less relevant roles, 2-3 is enough. Use your judgement.
   - **BOLD key technologies and tools** in each bullet by wrapping them in **double asterisks**. \
For example: "Built a CI/CD pipeline using **AWS CodePipeline** and **CodeBuild**, reducing deployment time by 50%."
   - You MAY adjust job titles slightly to better align with the target role. For example, \
if the base CV says "Software Engineer" but the job listing is for a DevOps role, you can adjust \
to "Software & DevOps Engineer" or similar — keep it honest but optimize for relevance. \
However, NEVER inflate seniority level. Do NOT add "Senior", "Lead", "Staff", "Principal", or \
similar seniority prefixes that are not in the original title.
   - If the job listing requires technologies the candidate hasn't explicitly listed, you MAY \
weave them naturally into existing bullet points as supplementary mentions, or add a small new \
bullet point that lightly claims familiarity. Keep additions inside the experience bullets. \
For example, if they use Kubernetes heavily, mentioning Helm in a bullet is fine.
   - The "technologies" field for each experience entry must only include tools explicitly referenced \
in the bullets for that role. Do not introduce new technologies in this field that aren't mentioned in the bullets.
   - Avoid overusing em dashes (—). Use commas, periods, or semicolons for variety. One or two em dashes \
across the entire CV is fine, but they should not appear in every bullet.
3. SKILLS: Filter and reorder skills to lead with those most relevant to this role. \
If you added a technology in the experience bullets above, you may also list it here — but the \
primary home for added tech is in the bullet points, not standalone in this section.
4. HIGHLIGHTED TECHNOLOGIES: Surface technologies from the base CV that the candidate \
knows but did not lead with. Technologies you wove into experience bullets may also appear here.
5. EDUCATION and PROJECTS and CERTIFICATIONS: Pass through unchanged. Always include ALL \
certifications from the base CV — never omit any, even if they seem unrelated to the role.
6. CONTACT: Pass through unchanged.
7. TAILORING NOTES: Provide a list of 5-10 notes explaining what you changed and why. Include:
   - Job titles you adjusted and the reasoning
   - Technologies you added that weren't in the base CV and why they're reasonable
   - Key bullet rewrites and what job requirement they target
   - Any strategic decisions (e.g., emphasizing certain experience over others)

CLOSED-LOOP REASONING — use the gap_diff to guide CV tailoring:
- Emphasize "strong" matches prominently in bullets and summary.
- Expand and reframe "partial" matches using implicit evidence from the base CV. \
For partial matches, you MAY make reasonable inferences about responsibilities that are \
clearly implied by the candidate's role and seniority. For example, if someone establishes \
"incident response protocols", it is reasonable to infer they also perform root cause analysis \
and take corrective actions to prevent recurrence. Surface these implied responsibilities \
naturally in the bullets — do not present them as separate, unrelated claims.
- Do NOT attempt to compensate for "missing" requirements beyond honest representation.

Return ONLY a valid JSON object matching this exact schema — no markdown fences, no commentary:

{
  "contact": {"name": "<str>", "email": "<str>", "linkedin": "<str or null>",
               "github": "<str or null>", "phone": "<str or null>", "location": "<str or null>"},
  "summary": "<tailored summary>",
  "experience": [
    {
      "company": "<str>",
      "title": "<str>",
      "start": "<YYYY-MM>",
      "end": "<YYYY-MM or null>",
      "bullets": ["<rewritten bullet>"],
      "technologies": ["<tech>"]
    }
  ],
  "skills": ["<most relevant first>"],
  "education": [{"institution": "<str>", "degree": "<str>",
                   "field": "<str or null>", "year": "<int or null>"}],
  "projects": [{"name": "<str>", "description": "<str>",
                  "technologies": [], "url": "<str or null>"}],
  "certifications": ["<str>"],
  "highlighted_technologies": ["<surfaced tech from base CV>"],
  "tailoring_notes": ["<note explaining what you changed and why>"],
  "gap_diff": [
    {
      "requirement": "<requirement from job listing>",
      "match_level": "strong",
      "evidence": "<quote or reference from base CV>"
    },
    {
      "requirement": "<partially matched requirement>",
      "match_level": "partial",
      "evidence": "<implicit or related evidence from base CV>"
    },
    {
      "requirement": "<missing requirement>",
      "match_level": "missing",
      "evidence": ""
    }
  ]
}"""


_COT_PREAMBLE = """\
IMPORTANT — think step-by-step before producing the JSON output:

Step 1: Read the entire job listing carefully. Identify ALL requirements, technologies, \
and responsibilities mentioned — aim for 10-15 distinct requirements. Do not stop at 3-5.

Step 2: For EACH requirement, scan the ENTIRE base CV (all roles, all bullets) for evidence. \
Check for both direct keyword matches AND implicit signals. For each match, note the specific \
company, role, and bullet that provides evidence. Quote or paraphrase the evidence.

Step 3: Assign match_level (strong/partial/missing) for each requirement. A "partial" match \
must include an explanation of what implicit signal connects the evidence to the requirement.

Step 4: Using your gap analysis, rewrite each experience section. For "strong" matches, \
make the connection prominent. For "partial" matches, surface the implied experience. \
For "missing" matches, do not fabricate.

Step 5: Write 5-10 detailed tailoring notes. Each note should explain: what you changed, \
which specific job requirement it targets, and why the change is justified by the base CV.

Now produce the JSON output following all the instructions above.\n\n"""


def _build_system_prompt_for_chat() -> str:
    """Build system prompt with chain-of-thought preamble for chat-based providers.

    OpenAI and Gemini need explicit step-by-step reasoning instructions
    to produce exhaustive, detailed output comparable to Claude.
    """
    return _COT_PREAMBLE + _build_system_prompt()


def _build_user_prompt(base_cv: BaseCV, job_text: str) -> str:
    """Build the user prompt containing the CV and job listing data."""
    base_cv_yaml = _serialize_base_cv(base_cv)
    return f"""\
BASE CV (YAML format — the candidate's complete experience):
---
{base_cv_yaml}
---

JOB LISTING:
---
{job_text}
---

Analyze the job listing thoroughly. Extract ALL requirements (aim for 10-15). \
For each requirement, cite specific evidence from specific roles in the base CV. \
Then produce the tailored CV as a single JSON object."""


def _build_prompt(base_cv: BaseCV, job_text: str) -> str:
    """Build combined prompt for Claude CLI (no system message support).

    Concatenates system prompt + user prompt into a single string.
    """
    return _build_system_prompt() + "\n\n" + _build_user_prompt(base_cv, job_text)


# ---------------------------------------------------------------------------
# Public entry point — single combined Claude call
# ---------------------------------------------------------------------------


def run_pipeline(base_cv: BaseCV, job_text: str) -> tuple[TailoredCV, list[GapItem]]:
    """Full AI pipeline: analyze job + tailor CV in a single Claude call.

    Returns:
        (tailored_cv, gap_diff) where gap_diff is extracted from the combined response.
    """
    prompt = _build_prompt(base_cv, job_text)
    result = _invoke_with_retry(prompt, TailoredCV)
    return result, result.gap_diff
