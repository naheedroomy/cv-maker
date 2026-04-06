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

    # Normalize tailoring_notes: convert plain strings to structured dicts
    if "tailoring_notes" in data and isinstance(data["tailoring_notes"], list):
        normalized = []
        for note in data["tailoring_notes"]:
            if isinstance(note, str):
                normalized.append({
                    "section": "General",
                    "change": note,
                    "reason": "",
                    "action": "modified",
                })
            elif isinstance(note, dict):
                # Ensure all required fields exist
                normalized.append({
                    "section": note.get("section", "General"),
                    "change": note.get("change", str(note)),
                    "reason": note.get("reason", ""),
                    "action": note.get("action", "modified"),
                })
            else:
                normalized.append({
                    "section": "General",
                    "change": str(note),
                    "reason": "",
                    "action": "modified",
                })
        data["tailoring_notes"] = normalized

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


def _build_creativity_instructions(level: int) -> str:
    """Return creativity-level-specific instruction text.

    Levels 0-1 return restrictive instructions (prepended to system prompt).
    Level 2 returns empty string (default behavior — no modification).
    Levels 3-5 return permissive instructions (appended to system prompt).
    """
    if level == 0:
        return """\
CREATIVITY LEVEL: 0 — STRICT MODE
- Do NOT change any job titles. Use exact titles from the base CV.
- Do NOT add new bullet points. Only reorder existing bullets.
- Do NOT weave in technologies not explicitly listed in the base CV.
- Do NOT adjust the summary beyond minor word reordering.
- Do NOT make inferences about implied experience.
- Only reorder sections and bullets to prioritize relevance. Zero content changes.
"""
    if level == 1:
        return """\
CREATIVITY LEVEL: 1 — CONSERVATIVE MODE
- Do NOT adjust job titles. Keep original titles exactly.
- You MAY rewrite bullet points to emphasize relevant aspects, but do not add claims beyond what is explicitly stated.
- You MAY reorder skills and sections for relevance.
- Do NOT weave in technologies unless the candidate explicitly lists them.
- Do NOT make inferences about implied responsibilities.
- Keep the summary closely aligned with the base CV's original framing.
"""
    if level == 2:
        return ""
    if level == 3:
        return """\
CREATIVITY LEVEL: 3 — FORWARD MODE
Focus on ADDRESSING GAPS from the gap analysis:
- For "partial" matches, aggressively surface implicit connections. If the candidate's experience \
plausibly includes a requirement, make that connection explicit in a bullet.
- You MAY infer responsibilities that are clearly implied by the candidate's role and seniority \
(e.g., a senior engineer likely mentors juniors, a platform lead likely drives architectural decisions).
- You MAY adjust job titles more freely to align with the target role (still no seniority inflation).
- Be more assertive in the summary about positioning the candidate as a strong fit.
- Keep bullets CONCISE. Do not make them longer — make them more targeted. Add new short bullets \
rather than expanding existing ones into paragraphs.
"""
    if level == 4:
        return """\
CREATIVITY LEVEL: 4 — BOLD MODE
Actively fill gaps identified in the gap analysis:
- For "missing" requirements, you MAY add short bullet points claiming familiarity ONLY IF \
the technology is adjacent to tools already used in the base CV. Phrase as exposure, not ownership \
(e.g., "Gained exposure to Terraform through infrastructure provisioning workflows" — not \
"Architected infrastructure using Terraform").
- You MAY add technologies to the skills section that the candidate plausibly knows based on their stack.
- Job titles can be adjusted more significantly to align with the target role (still no seniority inflation).
- The summary should position the candidate as an excellent fit.
- Keep bullets SHORT and punchy — one accomplishment per bullet. Do NOT write paragraph-length bullets. \
Adding more short bullets is better than making fewer bullets longer.
- For each added claim, include the evidence basis in tailoring_notes so the candidate can verify.
"""
    if level == 5:
        return """\
CREATIVITY LEVEL: 5 — CREATIVE MODE
Maximize relevance by filling all gaps:
- You MAY fabricate plausible experience and technology claims to address "missing" requirements.
- Job titles can be rewritten to match the target role.
- The summary should present the candidate as a perfect fit.
- Add technologies and skills that would strengthen the application.
- Keep the same concise bullet format — short, punchy accomplishments. Do NOT write verbose bullets. \
The goal is more relevant content, not more words per bullet.
WARNING: Output at this level may contain fabricated claims. User assumes responsibility for accuracy.
"""
    return ""


def _build_system_prompt(creativity_level: int = 2) -> str:
    """Build the system prompt with instructions and output schema.

    Used by chat-based providers (OpenAI, Gemini) as the system message.
    Claude CLI concatenates this with the user prompt via _build_prompt().

    For creativity levels 0-1, restrictive instructions are PREPENDED.
    For level 2 (default), the prompt is returned unchanged.
    For creativity levels 3-5, permissive instructions are APPENDED.
    """
    instructions = _build_creativity_instructions(creativity_level)
    base_prompt = """\
You are a CV tailoring expert. Given a candidate's base CV and a job listing, you will:
1. Analyze the job requirements and compute a gap diff
2. Produce a tailored CV optimized for the role

BULLET SOURCE OF TRUTH:
The base CV is the ONLY source of truth. It contains EVERYTHING the candidate has done — \
every role, every bullet, every technology. Not every application needs every bullet. \
You may:
- Reorder, rewrite, split, or combine bullets from the base CV
- Surface implicit experience already evidenced in the base CV
- OMIT bullets that are irrelevant to this specific role
- Select the most relevant subset while keeping enough breadth for well-roundedness
You may NOT introduce entirely new experiences, responsibilities, or technologies that cannot \
be traced back to specific content in the base CV. If adding a new bullet, it must be a \
transformation or extraction of existing content — not a new claim.

Instructions:

GAP ANALYSIS:
- Extract key requirements and technologies from the job listing (aim for 10-15).
- For each requirement, evaluate the base CV for evidence. Consider both explicit mentions AND \
implicit signals (e.g., observability work implies monitoring and alerting; CI/CD work implies \
build, test, and deploy automation; Kubernetes work implies container orchestration and scaling).
- Assign a match_level: "strong" (direct evidence), "partial" (implicit/related), or "missing" (no evidence).
- PRIORITIZE requirements into tiers:
  Tier 1: Core technical stack (must-have technologies and platforms)
  Tier 2: Core responsibilities (e.g., CI/CD, observability, incident response)
  Tier 3: Secondary tools and nice-to-haves
- Focus CV tailoring primarily on Tier 1 and Tier 2. Do not over-optimize for Tier 3 requirements.
- Include this as "gap_diff" in the output.

ALLOWED IMPLICIT INFERENCES:
When a candidate's experience clearly implies adjacent skills, you may surface them. \
Allowed inference patterns:
- Technology adjacency: using a platform implies its standard tooling \
(e.g., Kubernetes implies deployments/scaling; AWS implies IAM/CloudWatch; CI/CD implies pipeline automation)
- Responsibility adjacency: a role implies its standard duties \
(e.g., incident response implies root cause analysis; platform work implies reliability engineering)
- Domain adjacency: deep work in one area implies awareness of related areas \
(e.g., backend development implies API design; infrastructure work implies monitoring)
You may NOT infer:
- Specific named tools not mentioned or clearly adjacent to the candidate's stack
- Organizational scope (team-wide or company-wide ownership) unless explicitly stated
- Leadership, mentoring, or management unless explicitly stated
- Certifications or formal qualifications

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
   - EVIDENCE ANCHORING: Every bullet must be traceable to (a) a specific bullet in the base CV, or \
(b) an allowed implicit inference from the rules above. If you cannot point to the source, do not include the claim.
   - Preserve the level of ownership indicated in the base CV. Do not upgrade action verbs \
(e.g., "worked on" to "led", "contributed to" to "architected") unless clearly supported by the original bullet.
   - You are NOT limited to the same number of bullets as the base CV. The base CV is a superset — \
select, combine, split, or drop bullets based on what is most relevant to THIS job. \
For highly relevant roles, 5-7 bullets is appropriate. For less relevant roles, 2-3 is enough. \
Drop bullets that add no value for this specific application. Each bullet should earn its place.
   - SIGNAL DENSITY: Each bullet should include a technology, an action, and an outcome where possible. \
Avoid generic phrasing like "worked on", "involved in", "helped with". Prefer concrete, measurable statements.
   - **BOLD key technologies and tools** in each bullet by wrapping them in **double asterisks**. \
For example: "Built a CI/CD pipeline using **AWS CodePipeline** and **CodeBuild**, reducing deployment time by 50%."
   - You MAY adjust job titles slightly to better align with the target role. For example, \
if the base CV says "Software Engineer" but the job listing is for a DevOps role, you can adjust \
to "Software & DevOps Engineer" or similar — keep it honest but optimize for relevance. \
However, NEVER inflate seniority level. Do NOT add "Senior", "Lead", "Staff", "Principal", or \
similar seniority prefixes that are not in the original title.
   - If the job listing requires technologies the candidate hasn't explicitly listed, you MAY \
weave them naturally into existing bullet points ONLY if they are adjacent to the candidate's \
known stack (per the inference rules above). Phrase as exposure, not ownership.
   - The "technologies" field for each experience entry must only include tools explicitly referenced \
in the bullets for that role. Do not introduce new technologies in this field that aren't mentioned in the bullets.
   - Avoid overusing em dashes (—). Use commas, periods, or semicolons for variety. One or two em dashes \
across the entire CV is fine, but they should not appear in every bullet.
   - Keep bullets CONCISE — one to two lines each. Do not write paragraph-length bullets. \
A good bullet is a single accomplishment with a measurable outcome, not a detailed narrative.
3. SKILLS: Filter and reorder skills to lead with those most relevant to this role. \
If you added a technology in the experience bullets above, you may also list it here — but the \
primary home for added tech is in the bullet points, not standalone in this section.
4. HIGHLIGHTED TECHNOLOGIES: Surface technologies from the base CV that the candidate \
knows but did not lead with. Technologies you wove into experience bullets may also appear here.
5. EDUCATION and PROJECTS and CERTIFICATIONS: Pass through unchanged. Always include ALL \
certifications from the base CV — never omit any, even if they seem unrelated to the role.
6. CONTACT: Pass through unchanged.
7. TAILORING NOTES: Provide a list of 5-10 structured notes. Each note must include:
   - "section": which part of the CV was changed (e.g., "Summary", "SyscoLabs experience", "Skills")
   - "change": what specifically was changed
   - "reason": why — which job requirement or strategic goal it targets
   - "action": one of "modified", "added", "removed", "reordered", or "unchanged"
   - "source": the evidence basis — either a quote/reference from the base CV, or which \
implicit inference rule justifies the change. This makes hallucination detectable.

CLOSED-LOOP REASONING — use the gap_diff to guide CV tailoring:
- Emphasize "strong" matches prominently in bullets and summary. These are Tier 1 priorities.
- Expand and reframe "partial" matches using the allowed implicit inference rules above. \
Surface implied responsibilities naturally in the bullets — do not present them as separate, unrelated claims.
- Do NOT attempt to compensate for "missing" requirements beyond honest representation.

FINAL CHECK:
- Before producing output, ensure:
  - Every bullet is supported by the base CV or the allowed inference rules above
  - No claim exceeds the level of ownership stated in the base CV
  - All Tier 1 requirements are clearly represented in the CV if any evidence exists

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
  "tailoring_notes": [
    {
      "section": "<CV section>",
      "change": "<what was changed>",
      "reason": "<why — which job requirement it targets>",
      "action": "modified",
      "source": "<base CV reference or inference rule>"
    }
  ],
  "gap_diff": [
    {
      "requirement": "<requirement from job listing>",
      "match_level": "strong",
      "tier": 1,
      "evidence": "<quote or reference from base CV>"
    },
    {
      "requirement": "<partially matched requirement>",
      "match_level": "partial",
      "tier": 2,
      "evidence": "<implicit or related evidence from base CV>"
    },
    {
      "requirement": "<missing requirement>",
      "match_level": "missing",
      "tier": 3,
      "evidence": ""
    }
  ]
}"""
    # Level 2 (default): no modification — return base prompt unchanged.
    if not instructions:
        return base_prompt
    # Levels 0-1: prepend restrictive instructions before the base prompt.
    if creativity_level <= 1:
        return instructions + "\n" + base_prompt
    # Levels 3-5: append permissive instructions after the base prompt.
    return base_prompt + "\n\n" + instructions


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


def _build_system_prompt_for_chat(creativity_level: int = 2) -> str:
    """Build system prompt with chain-of-thought preamble for chat-based providers.

    OpenAI and Gemini need explicit step-by-step reasoning instructions
    to produce exhaustive, detailed output comparable to Claude.
    """
    return _COT_PREAMBLE + _build_system_prompt(creativity_level)


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


def _build_prompt(base_cv: BaseCV, job_text: str, creativity_level: int = 2) -> str:
    """Build combined prompt for Claude CLI (no system message support).

    Concatenates system prompt + user prompt into a single string.
    """
    return _build_system_prompt(creativity_level) + "\n\n" + _build_user_prompt(base_cv, job_text)


# ---------------------------------------------------------------------------
# Public entry point — single combined Claude call
# ---------------------------------------------------------------------------


def run_pipeline(base_cv: BaseCV, job_text: str, creativity_level: int = 2) -> tuple[TailoredCV, list[GapItem]]:
    """Full AI pipeline: analyze job + tailor CV in a single Claude call.

    Returns:
        (tailored_cv, gap_diff) where gap_diff is extracted from the combined response.
    """
    prompt = _build_prompt(base_cv, job_text, creativity_level)
    result = _invoke_with_retry(prompt, TailoredCV)
    return result, result.gap_diff
