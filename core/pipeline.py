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
from enum import IntEnum

import yaml

logger = logging.getLogger(__name__)

from core.models import BaseCV, GapItem, TailoredCV

# ---------------------------------------------------------------------------
# Creativity levels
# ---------------------------------------------------------------------------


class Creativity(IntEnum):
    """Creativity level governs how freely the model may deviate from the base CV."""

    STRICT = 0       # Reorder only — zero content changes
    CONSERVATIVE = 1  # Rewrite for emphasis, no new claims
    DEFAULT = 2       # Surface implicit experience via inference rules
    FORWARD = 3       # Aggressively surface implicit connections
    BOLD = 4          # Add plausible adjacent-tech claims (flagged)
    CREATIVE = 5      # Fabrication allowed (user assumes responsibility)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_claude_cli_model() -> str:
    """Get Claude CLI model from env or default.

    NOTE: Per-user settings resolution now happens in the async get_provider()
    factory (core/providers/__init__.py), which passes cli_model to the
    ClaudeProvider constructor. This sync fallback only reads env vars.
    """
    return os.environ.get("CLAUDE_MODEL", "haiku")


def _invoke_claude(prompt: str, timeout: int = 300, cli_model: str = "") -> str:
    """Invoke claude -p and return raw stdout. Raises RuntimeError on failure."""
    model_name = cli_model or _get_claude_cli_model()
    logger.info("Claude CLI: invoking (timeout=%ds, prompt=%d chars)", timeout, len(prompt))
    t0 = time.monotonic()
    try:
        result = subprocess.run(  # noqa: S603
            ["claude", "-p", "--model", model_name, "--no-session-persistence"],  # noqa: S607
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
    """Extract JSON from LLM output, stripping markdown fences if present."""
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as first_err:
        m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
        else:
            # Include the actual parse error position for diagnosis
            pos = first_err.pos or 0
            ctx_start = max(0, pos - 60)
            ctx_end = min(len(text), pos + 60)
            raise ValueError(
                f"No JSON object found in LLM output: {text[:300]!r}\n"
                f"  Parse error: {first_err.msg} at pos {pos}\n"
                f"  Context around error: ...{text[ctx_start:ctx_end]!r}..."
            )

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


def _invoke_with_retry(prompt: str, schema_cls, max_attempts: int = 3, cli_model: str = ""):
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
            raw = _invoke_claude(effective_prompt, cli_model=cli_model)
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
# Prompt builder — single parameterized prompt
# ---------------------------------------------------------------------------

# Per-concern rules keyed by creativity level thresholds.
# The builder picks the highest level <= the requested creativity via _resolve_rule().

_RULES: dict[str, dict[int, str]] = {
    "titles": {
        0: "Do NOT change any job titles. Use exact titles from the base CV.",
        1: "Do NOT change any job titles. Use exact titles from the base CV.",
        2: (
            "You MAY adjust job titles slightly to align with the target role "
            "(e.g., 'Software Engineer' -> 'Software & DevOps Engineer'). "
            "NEVER inflate seniority — do not add Senior/Lead/Staff/Principal."
        ),
        3: (
            "You MAY adjust job titles more freely to align with the target role. "
            "NEVER inflate seniority — do not add Senior/Lead/Staff/Principal."
        ),
        4: (
            "Job titles can be adjusted significantly to align with the target role. "
            "NEVER inflate seniority — do not add Senior/Lead/Staff/Principal."
        ),
        5: "Job titles can be rewritten to match the target role exactly.",
    },
    "bullets": {
        0: (
            "Do NOT rewrite or add bullets. Only REORDER existing bullets by relevance. "
            "Zero content changes."
        ),
        1: (
            "You MAY rewrite bullets to emphasize relevant aspects, but every claim must be "
            "explicitly stated in the base CV. No inferences, no new claims. "
            "When in doubt, keep a bullet rather than remove it."
        ),
        2: (
            "You MAY rewrite, split, combine, or reorder bullets. Every bullet must trace back "
            "to a specific bullet in the base CV or an allowed implicit inference (see below). "
            "When in doubt, keep a bullet rather than remove it — a slightly less relevant bullet "
            "is better than a gap that makes the candidate look inexperienced."
        ),
        3: (
            "Aggressively surface implicit connections. If the candidate's experience plausibly "
            "includes a requirement, make that connection explicit. Add short new bullets "
            "rather than inflating existing ones.\n"
            "SOFT FABRICATION: You MAY rewrite 1-2 bullets per role to swap equivalent "
            "technologies to match the target stack (see SUBSTITUTION rules below). You MAY "
            "also add 1-2 new bullets per role claiming hands-on experience with the target "
            "stack IF the candidate has demonstrable equivalent experience. Keep fabricated "
            "bullets concise, realistic, and interview-defensible. The candidate reviews all "
            "fabricated content before submission."
        ),
        4: (
            "Actively fill gaps. For 'missing' requirements, you MAY add short bullets claiming "
            "familiarity ONLY for technologies adjacent to the candidate's known stack. "
            "Phrase as exposure, not ownership (e.g., 'Gained exposure to X through Y workflows'). "
            "Document the evidence basis in tailoring_notes for candidate review."
        ),
        5: (
            "Maximize relevance by filling all gaps. You MAY fabricate plausible experience "
            "to address missing requirements. Keep the same concise bullet format. "
            "WARNING: Output may contain fabricated claims — user assumes responsibility."
        ),
    },
    "skills_injection": {
        0: "Do NOT add any technologies not already listed in the base CV.",
        1: "Do NOT add any technologies not already listed in the base CV.",
        2: (
            "If you wove a technology into experience bullets via inference, you MAY also "
            "list it in skills. List skills as plain names — no parenthetical qualifiers, "
            "no 'alternative:' or 'similar to:' annotations."
        ),
        3: (
            "You MAY add technologies to the skills section that are clearly implied by the "
            "candidate's stack. Plain names only."
        ),
        4: (
            "You MAY add technologies the candidate plausibly knows based on their stack. "
            "Plain names only."
        ),
        5: "Add any technologies that would strengthen the application. Plain names only.",
    },
    "summary": {
        0: "Do NOT adjust the summary beyond minor word reordering.",
        1: "Keep the summary closely aligned with the base CV's original framing.",
        2: (
            "Position the candidate to match the role's core identity. Reflect seniority signals "
            "like ownership and cross-team impact. Prioritize the top 3 themes from the job description.\n"
            "Use Chain of Density: draft a summary, then compress by replacing filler adjectives "
            "with specific entities (tools, metrics, domain terms) from the base CV WITHOUT "
            "increasing word count. Final summary: 2-4 sentences of dense, factual text. "
            "No hollow phrases like 'results-driven professional' or 'proven track record'."
        ),
        3: (
            "Be assertive in positioning the candidate as a strong fit for the role.\n"
            "Use Chain of Density: draft, then compress — replace every filler adjective with a "
            "specific tool, metric, or domain term. 2-4 dense sentences. If a phrase could apply "
            "to any engineer, cut it and replace with something only THIS candidate can claim."
        ),
        4: "The summary should position the candidate as an excellent fit.",
        5: "The summary should present the candidate as a perfect fit.",
    },
    "tone": {
        0: "",
        2: (
            "WRITING STYLE — this is critical for quality:\n"
            "Do NOT pad bullets with filler adjectives or adverbs. Specifically avoid: "
            "'robust', 'comprehensive', 'seamless', 'cutting-edge', 'critical', 'significant', "
            "'efficiently', 'effectively', 'proactively', 'strategically', 'innovative'.\n"
            "Do NOT inflate the base CV's language. If the base CV says 'Built a CI/CD pipeline', "
            "do NOT rewrite it as 'Developed a comprehensive, robust CI/CD pipeline'. "
            "Match or tighten the base CV's tone — never expand it.\n"
            "The base CV bullets are already well-written. Your job is to SELECT, REORDER, "
            "and LIGHTLY REWRITE for relevance — not to 'improve' the prose. "
            "Shorter is better. If a rewrite is longer than the original, you're probably adding filler.\n"
            "Do NOT add trailing qualifiers like 'ensuring reliability and performance' or "
            "'improving efficiency and scalability' unless the base CV included them."
        ),
    },
    "reorder": {
        0: (
            "Within each role, REORDER bullets so the most JD-relevant bullets appear first. "
            "This applies at every creativity level — even when content cannot be changed, order can."
        ),
    },
    "core_competencies": {
        0: (
            "Select 6-10 of the candidate's TOP skills/technologies from their base CV, "
            "ordered by relevance to this job listing. These come from the CANDIDATE'S stack, "
            "not the JD's language — do NOT parrot JD phrases back. "
            "Mix concrete tools (Kubernetes, Terraform, AWS, Datadog) with key capabilities "
            "(CI/CD, GitOps, IaC) that the candidate genuinely has. "
            "Keep each entry to 1-3 words. Include certification labels if relevant (e.g., 'Kubernetes (CKAD)'). "
            "Return as the 'core_competencies' array."
        ),
    },
    "pruning": {
        0: (
            "A bullet that doesn't directly match a Tier 1 requirement but demonstrates "
            "valuable experience, impact, or breadth should be KEPT — its presence does not "
            "harm the CV, and its absence creates a gap. Only drop bullets that actively "
            "weaken the CV (e.g., trivially irrelevant to any aspect of the role). "
            "Bias toward INCLUSION over exclusion."
        ),
    },
    "inference": {
        0: "Do NOT make any inferences about implied experience.",
        1: "Do NOT make any inferences about implied responsibilities.",
        2: (
            "Implicit inference rules — these define what connections are valid:\n"
            "- Technology adjacency: using a platform implies its standard tooling "
            "(e.g., Kubernetes -> deployments/scaling/ingress; AWS -> IAM/CloudWatch)\n"
            "- Infrastructure fundamentals: running cloud workloads implies foundational networking, "
            "security, and routing knowledge "
            "(e.g., AWS + Kubernetes -> VPC, subnets, DNS, security groups, load balancers, ingress)\n"
            "- Responsibility adjacency: a role implies its standard duties "
            "(e.g., incident response -> root cause analysis)\n"
            "- Domain adjacency: deep work in one area implies awareness of related areas\n"
            "You may NOT infer: specific named tools not adjacent to the stack, organizational scope, "
            "leadership/mentoring, or certifications."
        ),
        # Levels 3-5 inherit level 2 inference rules — the bullet rules above
        # govern what the model is allowed to DO with those inferences.
    },
    "substitution": {
        0: "Do NOT substitute any technologies, tools, or platforms.",
        2: "Do NOT substitute any technologies, tools, or platforms.",
        3: (
            "SELECTIVE STACK SUBSTITUTION — swap equivalent technologies in SOME roles when the "
            "JD requires a different tool, but preserve the candidate's real stack diversity.\n"
            "Valid swap categories:\n"
            "- Cloud providers: AWS <-> GCP <-> Azure (EC2/Compute Engine/VM, S3/GCS/Blob Storage, "
            "EKS/GKE/AKS, RDS/Cloud SQL/Azure SQL, Lambda/Cloud Functions/Azure Functions, "
            "SQS/Pub-Sub/Service Bus, CloudWatch/Cloud Monitoring/Azure Monitor, "
            "CloudFormation/Deployment Manager/ARM Templates, IAM/IAM/Entra ID)\n"
            "- CI/CD: GitHub Actions <-> GitLab CI <-> Jenkins <-> CircleCI <-> Azure DevOps\n"
            "- IaC: Terraform <-> Pulumi <-> CloudFormation <-> CDK <-> ARM Templates\n"
            "- Monitoring: Datadog <-> Prometheus+Grafana <-> New Relic <-> Dynatrace\n"
            "- Databases: PostgreSQL <-> MySQL <-> SQL Server (relational); "
            "Redis <-> Memcached (cache); MongoDB <-> DynamoDB <-> Firestore (document)\n"
            "- Messaging: Kafka <-> RabbitMQ <-> SQS <-> Pub/Sub\n"
            "CRITICAL DIVERSITY RULE for Level 3:\n"
            "- Do NOT uniformly replace the same technology across ALL roles. A candidate's "
            "history should show realistic stack diversity — it is normal for different companies "
            "to use different stacks.\n"
            "- Swap the target stack into AT MOST 1-2 of the most relevant roles (ideally the "
            "most recent or most aligned with the JD). Leave remaining roles on their ORIGINAL "
            "stack.\n"
            "- Example: if the candidate used AWS at 3 companies and the JD wants GCP, swap "
            "to GCP at ONE company (the most relevant one), keep AWS at the others. The result "
            "shows the candidate knows GCP AND has breadth across cloud providers.\n"
            "Other rules:\n"
            "- Swap the technology name but keep the achievement, metrics, and scope intact.\n"
            "- You MAY add 1-2 new bullets per role using the target stack IF the candidate "
            "has equivalent experience. Keep them concise and interview-defensible.\n"
            "- MANDATORY: document every swap in tailoring_notes with action 'substituted' "
            "and every added bullet with action 'soft-fabricated'. The source field MUST name "
            "the original technology and the equivalence basis.\n"
            "- NEVER put annotations like '(substituted)', '(soft-fabricated)', or any action "
            "labels inside the actual bullet text. These labels belong ONLY in tailoring_notes. "
            "The CV bullets must read as natural, clean text with no metadata visible.\n"
            "- Do NOT swap across categories (e.g., do not swap a database for a message queue).\n"
            "- Do NOT fabricate metrics, team sizes, or project scopes — only swap tool names."
        ),
        4: (
            "AGGRESSIVE STACK SUBSTITUTION — swap equivalent technologies across ALL roles "
            "to present a unified stack aligned with the JD. The Level 3 diversity constraint "
            "is LIFTED — you may replace the same technology everywhere. Additionally, you MAY "
            "make broader technology swaps even without direct equivalence, as long as the "
            "candidate's experience demonstrates the underlying patterns and concepts."
        ),
        5: "Unrestricted technology substitution and fabrication.",
    },
}


def _resolve_rule(rule_name: str, level: int) -> str:
    """Pick the instruction for the highest defined threshold <= level."""
    levels = _RULES[rule_name]
    applicable = [k for k in sorted(levels) if k <= level]
    if not applicable:
        applicable = [min(levels)]
    return levels[applicable[-1]]


def _build_prompt(base_cv: BaseCV, job_text: str, creativity_level: int = 2) -> str:
    """Build a single, self-consistent prompt parameterized by creativity level.

    Instead of layering contradictory instructions, each concern (titles, bullets,
    skills, summary, inference) is stated exactly once at the appropriate strictness.
    """
    level = max(0, min(5, creativity_level))
    base_cv_yaml = _serialize_base_cv(base_cv)

    title_rule = _resolve_rule("titles", level)
    bullet_rule = _resolve_rule("bullets", level)
    skills_rule = _resolve_rule("skills_injection", level)
    summary_rule = _resolve_rule("summary", level)
    inference_rule = _resolve_rule("inference", level)
    tone_rule = _resolve_rule("tone", level)
    reorder_rule = _resolve_rule("reorder", level)
    core_comp_rule = _resolve_rule("core_competencies", level)
    pruning_rule = _resolve_rule("pruning", level)
    substitution_rule = _resolve_rule("substitution", level)

    level_label = Creativity(level).name

    prompt = f"""\
You are a no-nonsense CV optimizer. You despise corporate fluff, filler adjectives, and \
AI-sounding prose. Your job is to make this CV hit hard with specific facts and metrics, \
not vague claims. Every word must earn its place.

CREATIVITY LEVEL: {level} ({level_label})

---
STEP 1 — GAP ANALYSIS

Extract 10-15 key requirements from the job listing. For each:
- Scan the ENTIRE base CV for evidence (all roles, all bullets). Check both explicit mentions and implicit signals.
- Assign match_level: "strong" (direct evidence), "partial" (implicit/related), or "missing" (no evidence).
- Assign tier: 1 (core tech stack), 2 (core responsibilities), 3 (nice-to-haves).
- Tier prioritization guides EMPHASIS, not ELIMINATION. Do not remove valuable experience just because it is Tier 3.

---
STEP 2 — TAILORED CV

Use the gap analysis to guide tailoring.

TITLES: {title_rule}

SUMMARY: {summary_rule}
Do NOT mention expected/upcoming certifications in the summary — only earned ones. But they MUST still appear in the certifications section.
Do NOT use **bold** markers in the summary.
The summary MUST reflect: the target role identity as stated in the job listing, and at least 2 core Tier 1 technologies the candidate demonstrably has.

EXPERIENCE:
{bullet_rule}
Additional constraints:
- Preserve exact role structure from the base CV. If the base CV has ONE entry for a company, output exactly ONE entry. Do NOT split a single role into multiple entries.
- Never change dates (start, end) from the base CV.
- Keep reverse chronological order.
- Write natural, professional bullets — avoid keyword-stuffing or directly reusing phrases from the job listing.
- Preserve ownership levels from the base CV. Do not upgrade verbs ("worked on" -> "led") unless clearly supported.
- Bullet count per role: MINIMUMS are 4-6 for highly relevant, 3-5 for moderate, 2-3 for any included role. These are FLOORS, not ceilings. If the base CV has 7 bullets for a role, you may keep all 7 — do NOT drop bullets just to fit a number. Only remove a bullet if it actively adds zero value for this specific application.
- Signal density: prefer a technology, an action, and an outcome per bullet. Avoid "worked on", "involved in", "helped with". But do NOT merge or remove bullets just to increase density — preserving meaningful experience matters more.
- **Bold** key technologies in bullets.
- Keep bullets concise — one accomplishment each, 1-2 lines max.
- The "technologies" field per role must only list tools referenced in that role's bullets.
- Avoid overusing em dashes; vary punctuation.
- Skills and highlighted_technologies: plain names only — no parenthetical qualifiers or "alternative:" annotations.
{tone_rule}

BULLET REWRITING EXAMPLES (style anchor — mimic the transformation pattern, not the content):

BEFORE: "Responsible for managing cloud infrastructure and ensuring system reliability across multiple environments"
AFTER: "Managed 40+ EC2 instances across 3 AWS regions. 99.95% uptime over 18 months."

BEFORE: "Developed and implemented comprehensive CI/CD pipelines that significantly improved deployment efficiency for the engineering team"
AFTER: "Built CI/CD pipeline with **GitHub Actions**. Cut deploy time from 45 min to 6 min. Team shipped daily instead of weekly."

BULLET ORDERING:
{reorder_rule}

PRUNING POLICY:
{pruning_rule}

IMPLICIT INFERENCE RULES:
{inference_rule}

SUBSTITUTION:
{substitution_rule}

SKILLS: Filter and reorder to lead with the most relevant.
{skills_rule}

HIGHLIGHTED TECHNOLOGIES: Surface technologies from the base CV that the candidate knows but did not lead with. Plain names only.

CORE COMPETENCIES:
{core_comp_rule}

EDUCATION, PROJECTS, CERTIFICATIONS, LANGUAGES: Pass through unchanged. Include ALL certifications from the base CV — both earned AND expected/upcoming. NEVER drop a certification. Languages and work_authorization are direct copies — never modify them.

CONTACT: Pass through unchanged.

---
STEP 3 — TAILORING NOTES (5-10)

Each note must include:
- "section": which CV section was changed
- "change": what was changed
- "reason": which job requirement it targets
- "action": one of "modified", "added", "removed", "reordered", "unchanged", "substituted", "soft-fabricated"
- "source": the base CV reference or inference rule that justifies the change
For "substituted": source MUST name the original technology (e.g., "AWS EC2 -> GCP Compute Engine")
For "soft-fabricated": source MUST explain the equivalence basis (e.g., "Candidate has 3 years AWS; GCP equivalent added for JD alignment")

---
ALIGNMENT CHECKS (apply before producing output):
- Every Tier 1 requirement with explicit evidence in the base CV MUST appear in at least one bullet.
- For every Tier 1 requirement marked "partial" in the gap analysis: check which inference rule connects the candidate's experience to the requirement. Then ensure at least one bullet or the summary explicitly surfaces that connection. If it doesn't, add or rewrite a bullet to make the connection visible.
- No bullet may exceed the ownership level stated in the base CV.
- No role compressed below the minimum bullet count: every experience entry MUST have at \
least 2 bullet points. If a role in the base CV has 2 or fewer bullets, keep all of them — \
optimize wording but never remove. Never return an experience entry with an empty bullets list.
- The CV reflects both depth (target alignment) and breadth (full experience).
- Optimize for BOTH relevance and coverage — not just a narrow match to the job listing.

---
BASE CV:
{base_cv_yaml}
---
JOB LISTING:
{job_text}
---

Return ONLY a valid JSON object (no markdown fences, no commentary) matching this schema:

{{
  "contact": {{"name": "<str>", "email": "<str>", "linkedin": "<str or null>",
               "github": "<str or null>", "phone": "<str or null>", "location": "<str or null>",
               "work_authorization": "<str or null — pass through unchanged>"}},
  "summary": "<tailored summary>",
  "experience": [
    {{
      "company": "<str>",
      "title": "<str>",
      "location": "<str or null>",
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
  "languages": [{{"language": "<str>", "level": "<str>"}}],
  "core_competencies": ["<JD-derived keyword phrase>"],
  "highlighted_technologies": ["<surfaced tech>"],
  "tailoring_notes": [
    {{
      "section": "<CV section>",
      "change": "<what>",
      "reason": "<why>",
      "action": "modified",
      "source": "<evidence>"
    }}
  ],
  "gap_diff": [
    {{
      "requirement": "<str>",
      "match_level": "strong|partial|missing",
      "tier": 1,
      "evidence": "<str>"
    }}
  ]
}}"""
    return prompt


def _build_system_prompt_for_chat(creativity_level: int = 2) -> str:
    """Build system prompt for chat-based providers (OpenAI, Gemini).

    These providers need explicit chain-of-thought instructions
    to produce exhaustive output comparable to Claude.
    The CoT preamble is prepended to the system message;
    the CV + job listing go in the user message via _build_user_prompt().
    """
    level = max(0, min(5, creativity_level))
    level_label = Creativity(level).name

    title_rule = _resolve_rule("titles", level)
    bullet_rule = _resolve_rule("bullets", level)
    skills_rule = _resolve_rule("skills_injection", level)
    summary_rule = _resolve_rule("summary", level)
    inference_rule = _resolve_rule("inference", level)
    tone_rule = _resolve_rule("tone", level)
    reorder_rule = _resolve_rule("reorder", level)
    core_comp_rule = _resolve_rule("core_competencies", level)
    pruning_rule = _resolve_rule("pruning", level)
    substitution_rule = _resolve_rule("substitution", level)

    return f"""\
IMPORTANT — think step-by-step before producing the JSON output:

Step 1: Read the entire job listing. Identify ALL requirements, technologies, and responsibilities (aim for 10-15).
Step 2: For EACH requirement, scan the ENTIRE base CV for evidence. Note the specific company, role, and bullet. Quote or paraphrase.
Step 3: Assign match_level (strong/partial/missing) and tier (1/2/3) for each.
Step 4: Rewrite each experience section guided by the gap analysis.
Step 5: Write 5-10 detailed tailoring notes with evidence references.

Now produce the JSON output following all instructions below.

---

You are a no-nonsense CV optimizer. You despise corporate fluff, filler adjectives, and \
AI-sounding prose. Your job is to make this CV hit hard with specific facts and metrics, \
not vague claims. Every word must earn its place.

CREATIVITY LEVEL: {level} ({level_label})

TITLES: {title_rule}

SUMMARY: {summary_rule}
Do NOT mention expected/upcoming certifications in the summary — only earned ones. No **bold** in the summary.
Must reflect: target role identity and at least 2 Tier 1 technologies the candidate has.

EXPERIENCE:
{bullet_rule}
- Preserve exact role structure from base CV. One entry per company = one output entry. Do NOT split roles.
- Preserve dates and reverse chronological order. Natural, professional language — no keyword-stuffing.
- Preserve ownership levels. Don't upgrade verbs unless supported.
- Bullet count MINIMUMS: 4-6 (high relevance), 3-5 (moderate), 2-3 (any role). These are FLOORS, not ceilings — if the base CV has more bullets, keep them unless a bullet adds zero value.
- Signal density: prefer technology + action + outcome per bullet. But do NOT merge/remove bullets just for density.
- **Bold** key technologies. Concise — 1 accomplishment per bullet, 1-2 lines max.
- "technologies" field per role: only tools referenced in that role's bullets.
- Skills and highlighted_technologies: plain names only — no parenthetical qualifiers.
{tone_rule}

BULLET REWRITING EXAMPLES (style anchor — mimic the transformation pattern, not the content):

BEFORE: "Responsible for managing cloud infrastructure and ensuring system reliability across multiple environments"
AFTER: "Managed 40+ EC2 instances across 3 AWS regions. 99.95% uptime over 18 months."

BEFORE: "Developed and implemented comprehensive CI/CD pipelines that significantly improved deployment efficiency for the engineering team"
AFTER: "Built CI/CD pipeline with **GitHub Actions**. Cut deploy time from 45 min to 6 min. Team shipped daily instead of weekly."

BULLET ORDERING:
{reorder_rule}

PRUNING POLICY:
{pruning_rule}

INFERENCE RULES:
{inference_rule}

SUBSTITUTION:
{substitution_rule}

SKILLS: {skills_rule}

HIGHLIGHTED TECHNOLOGIES: Surface known-but-not-leading technologies from the base CV. Plain names only.

CORE COMPETENCIES:
{core_comp_rule}

EDUCATION, PROJECTS, CERTIFICATIONS, LANGUAGES: Pass through unchanged. Include ALL certifications — both earned AND expected/upcoming. NEVER drop any. Languages and work_authorization are direct copies.
CONTACT: Pass through unchanged.

TAILORING NOTES (5-10): Each with section, change, reason, action (modified/added/removed/reordered/unchanged/substituted/soft-fabricated), source.
For "substituted": source MUST name the original technology (e.g., "AWS EC2 -> GCP Compute Engine").
For "soft-fabricated": source MUST explain the equivalence basis.

GAP ANALYSIS: 10-15 requirements, each with requirement, match_level, tier, evidence.
Tier prioritization guides EMPHASIS, not ELIMINATION.

ALIGNMENT CHECKS:
- Every Tier 1 requirement with explicit base CV evidence MUST appear in at least one bullet.
- For every Tier 1 "partial" match: identify the inference rule that connects the candidate's experience to the requirement. Ensure at least one bullet surfaces that connection. If not, add or rewrite one.
- No bullet exceeds stated ownership. No role below minimum bullet count (2). \
Never return empty bullets lists. If a role has 2 or fewer bullets, keep all of them.
- Balance depth (target alignment) and breadth (full experience).

Return ONLY valid JSON (no fences, no commentary) matching the schema provided in the user message."""


def _build_user_prompt(base_cv: BaseCV, job_text: str) -> str:
    """Build the user prompt containing the CV and job listing data."""
    base_cv_yaml = _serialize_base_cv(base_cv)
    return f"""\
BASE CV:
---
{base_cv_yaml}
---

JOB LISTING:
---
{job_text}
---

Analyze the job listing thoroughly. Extract ALL requirements (aim for 10-15). \
For each, cite specific evidence from the base CV. Then produce the tailored CV \
as a single JSON object matching this schema:

{{
  "contact": {{"name": "<str>", "email": "<str>", "linkedin": "<str or null>",
               "github": "<str or null>", "phone": "<str or null>", "location": "<str or null>",
               "work_authorization": "<str or null — pass through unchanged>"}},
  "summary": "<tailored summary>",
  "experience": [
    {{
      "company": "<str>",
      "title": "<str>",
      "location": "<str or null>",
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
  "languages": [{{"language": "<str>", "level": "<str>"}}],
  "core_competencies": ["<JD-derived keyword phrase>"],
  "highlighted_technologies": ["<surfaced tech>"],
  "tailoring_notes": [
    {{
      "section": "<CV section>",
      "change": "<what>",
      "reason": "<why>",
      "action": "modified",
      "source": "<evidence>"
    }}
  ],
  "gap_diff": [
    {{
      "requirement": "<str>",
      "match_level": "strong|partial|missing",
      "tier": 1,
      "evidence": "<str>"
    }}
  ]
}}"""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_pipeline(base_cv: BaseCV, job_text: str, creativity_level: int = 2, cli_model: str = "") -> tuple[TailoredCV, list[GapItem]]:
    """Full AI pipeline: analyze job + tailor CV in a single Claude call.

    Returns:
        (tailored_cv, gap_diff) where gap_diff is extracted from the combined response.
    """
    prompt = _build_prompt(base_cv, job_text, creativity_level)
    result = _invoke_with_retry(prompt, TailoredCV, cli_model=cli_model)
    return result, result.gap_diff
