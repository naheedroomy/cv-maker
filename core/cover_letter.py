"""Cover letter generation — prompt templates, Pydantic model, and provider-agnostic generation."""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel

from cv_maker.models import BaseCV, GapItem, TailoredCV
from cv_maker.pipeline import _extract_json, _invoke_with_retry, _serialize_base_cv
from cv_maker.providers import get_provider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tone instructions
# ---------------------------------------------------------------------------

_TONE_INSTRUCTIONS: dict[str, str] = {
    "formal": (
        "Write in a traditional corporate style. Use full sentences, formal greetings "
        "('Dear Hiring Manager'), and professional closings ('Sincerely'). "
        "Address the hiring manager formally."
    ),
    "professional": (
        "Write directly and clearly. No fluff. Lead with specifics. "
        "'Your role aligns with my 4 years of K8s experience' not "
        "'I am excited to apply for this wonderful opportunity.'"
    ),
    "confident": (
        "Write assertively with specific achievements. "
        "'I built a self-healing K8s platform that cut MTTR from 60 to 5 min' not "
        "'I have experience with Kubernetes.' Own your work."
    ),
    "direct": (
        "Facts only. No warmth, no personality, no flair. State what you did, "
        "what they need, and why it matches. Let the work speak."
    ),
    "casual": (
        "Write conversationally. Show personality. Use contractions. "
        "OK to use informal transitions and first person naturally."
    ),
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """\
You are writing a cover letter for a job application. You have access to:
1. The candidate's base CV (full background)
2. The job listing
3. The tailored CV (already optimized for this role) — this is your PRIMARY source
4. The gap analysis (what matched, what's partial, what's missing)
5. User notes (specific things to mention or emphasize)

TONE: {tone_instruction}

---
WHAT A COVER LETTER IS (AND IS NOT)

A cover letter is NOT a CV summary. The reader already has the CV. If your letter reads \
like a list of accomplishments with periods instead of bullet points, you have failed. \
A cover letter does what a CV cannot: it tells a story, shows personality, connects \
the dots between your experience and their specific needs, and gives the reader a sense \
of what it would be like to work with you.

Pick 2-3 proof points max. Go deep on each, not wide across many. One well-contextualized \
achievement is worth more than five listed ones.

Do NOT state obvious things like "I've uploaded my CV" or "as you can see from my resume." \
They know.

---
LENGTH AND STRUCTURE

200-300 words MAXIMUM. Count them. 3 paragraphs (not 4, not 5). \
Shorter is always better. Every sentence must earn its place. \
If you are over 300 words, you have too many proof points. Cut.

Paragraph 1 — THE HOOK (3-4 sentences):
Why this specific role at this specific company. Reference one concrete detail about the \
company from the job listing: their product, mission, scale, or tech stack. \
Do NOT use generic praise like "innovative company" or "industry leader." \
If the job listing names a hiring manager, address them by name. Otherwise use "Hi" or \
"Hello" for casual/direct tones, "Dear Hiring Manager" for formal/professional.

Paragraph 2 — PROOF POINTS (4-6 sentences):
Your 2-3 STRONGEST achievements from the tailored CV, matched to their top requirements. \
TWO to THREE. Not four. Not five. Not six. Pick the best and cut the rest. \
Contextualize and connect: explain WHY these achievements matter for THIS role. \
Do NOT copy bullet points from the CV verbatim. The reader already has your CV. \
Rephrase, connect, and add narrative context that bullets can't convey. \
Vary how you introduce achievements. Do NOT write "I've [verb]. I've [verb]. I've [verb]." \
That is a bullet list with periods. Use transitions, compound sentences, and varying subjects.

Paragraph 3 — CLOSE (1-3 sentences):
A concrete, specific next step. Not "I look forward to discussing." \
Reference something specific you could walk them through or discuss. \
Keep it tight. One sentence is often enough.

---
GAP HANDLING

Use the gap analysis to decide what to emphasize and what to address:

- "strong" matches: These are your proof points. Feature them prominently.
- "partial" matches: Where you have adjacent/transferable experience, you MAY briefly \
acknowledge the specific tool gap while asserting your transferable skill. Frame it as \
capability, not apology. Example: "Your stack uses GitLab CI. I've built equivalent \
pipelines in GitHub Actions and ArgoCD, so the patterns transfer directly." \
Only do this for 1-2 partial matches max. Do not turn the letter into a list of \
tool translations.
- "missing" matches: Do NOT mention these. Do not apologize for gaps. Do not say \
"while I lack experience in X." Focus entirely on what you bring.

General: One sentence near the close expressing genuine interest in growing with the \
team's specific stack is fine. Frame as enthusiasm, not deficiency. \
"Keen to get hands-on with [specific tool from listing]" not \
"I am eager to learn and grow."

---
ANTI-AI WRITING RULES (mandatory — violations will be caught in the self-critique step):

1. NO SIGNIFICANCE INFLATION: Never use "pivotal", "testament to", "underscores",
   "crucial role", "shaping the future of". Say what happened, not how important it was.
   BAD: "This role is a pivotal opportunity to shape the future of cloud infrastructure."
   GOOD: "You need someone to migrate 200 services to Kubernetes. I did that at Sysco."

2. NO PROMOTIONAL LANGUAGE: Never use "passionate about", "thrilled to apply",
   "committed to excellence", "vibrant", "showcase". These are AI tells.
   BAD: "I am passionate about cloud-native technologies and thrilled to apply."
   GOOD: "I like building things that stay up. Kubernetes and I get along."

3. SIMPLE VERBS: "I built" not "I spearheaded the development of". "I fixed" not
   "I addressed challenges in". "I connect X and Y" not "I serve as the bridge between X and Y".
   BAD: "I spearheaded the development of a comprehensive observability platform."
   GOOD: "I built the observability platform. Datadog dashboards, alert routing, the whole stack."

4. NO RULE-OF-THREE CLUSTERS: Never list three abstract nouns together.
   BAD: "innovation, collaboration, and impact"
   GOOD: Pick one. Be specific about it.

5. NO GENERIC CONCLUSIONS: Never write "I look forward to the opportunity to discuss"
   or "I would welcome the chance to contribute". End with something specific.
   BAD: "I look forward to discussing how I can contribute to your team."
   GOOD: "Happy to walk through the K8s migration timeline. My calendar's open."

6. NO PARTICIPIAL PADDING: Never tack on "leveraging", "contributing to",
   "fostering", "showcasing", "emphasizing". These are filler.
   BAD: "...leveraging my expertise in cloud infrastructure, contributing to team success."
   GOOD: Cut it. The sentence was done before the -ing phrase.

7. NO FILLER PHRASES: "To" not "In order to". "I can" not "I have the ability to".
   "Because" not "Due to the fact that".

8. VARY SENTENCE RHYTHM: Mix short punchy sentences with longer ones.
   Not every sentence should be 15-20 words. Some should be 5. Some 30.

9. HAVE OPINIONS, DON'T HEDGE: "I can" not "I could potentially be able to".
   "This fits" not "I believe this could potentially be a good fit".

10. SPECIFICITY OVER SCOPE: Concrete facts beat broad claims.
    BAD: "I have extensive experience in cloud infrastructure."
    GOOD: "I ran 340 pods across 3 clusters at Sysco Labs for 2 years."

11. NO EM DASHES OR EM DASH SUBSTITUTES: Do not use em dashes (—) at all. Zero.
    Also do not simulate em dashes with parenthetical injections mid-sentence.
    BAD: "built GitOps workflows with ArgoCD and Terraform (fully reproducible AWS environments)"
    BAD: "engineered CI/CD pipelines — eliminating manual overhead"
    GOOD: "Built GitOps workflows with ArgoCD and Terraform. Every environment is reproducible."
    If you need to add context, use a new sentence. Not a parenthetical. Not a dash.

12. NO ABSTRACT ENTHUSIASM: Do not write "I am eager to learn" or "excited to grow."
    If you want to express interest in learning something, name the specific thing.
    BAD: "I am eager to learn and grow with your team."
    GOOD: "Keen to dig into Helmfile. I've done similar work with plain Helm charts."

13. NO ACHIEVEMENT CHAINS OR BULLET-LIST-IN-DISGUISE: Do not string 3+ achievements
    into one sentence with commas or semicolons. Also do not write consecutive
    "I [verb]..." sentences. That is a bullet list with periods instead of bullet points.
    BAD: "I engineered CI/CD pipelines, built GitOps workflows, and integrated monitoring."
    BAD: "I've managed clusters. I've built pipelines. I've scaled services. I've operated databases."
    GOOD: "I engineered zero-touch CI/CD pipelines with GitHub Actions. On the IaC side,
    I built GitOps workflows with ArgoCD and Terraform that made every AWS environment
    reproducible."
    The cover letter is not a CV summary. 2-3 proof points max. Go deep, not wide.
    Vary sentence structure. Use transitions. Connect achievements to their needs.

---
PROCESS (execute all steps internally, return only the final JSON):

STEP 1: Write a 3-4 paragraph cover letter draft.
        Use the tailored CV as your PRIMARY source for achievements.
        Use the gap analysis to decide what to emphasize.
        Use the job listing for company-specific details.
        If user notes are provided, weave them naturally.

STEP 2: Self-critique. Read your draft as a hostile AI-detection reviewer.
        STRUCTURE CHECK: Count paragraphs. Must be exactly 3. If you have 4+, merge or cut.
        WORD COUNT CHECK: Count words. Must be 200-300. If over 300, you have too many
        proof points. Cut achievements, not context. Go from 5 proof points to 2-3.
        Check every sentence against the 13 anti-AI rules above.
        Check for CV bullet copying or CV summary tone.
        Check for generic company praise.
        Check em dash count (must be ZERO, not one, zero).
        Check for parenthetical mid-sentence injections that simulate em dashes.
        Check for achievement chains (3+ accomplishments in one sentence).
        Check for consecutive "I [verb]" sentences (bullet list in disguise).
        Check for dead weight ("I've uploaded my CV", "as you can see from my resume").
        Check for rule-of-three abstract noun clusters.
        Does this read like a PERSON wrote it, or like an AI summarized a CV?
        Find at least 3 issues. If you find fewer, look harder.

STEP 3: Rewrite the draft to fix every issue found.

STEP 4: Return ONLY valid JSON (no markdown fences):
{{"cover_letter_text": "<final revised text>", "self_critique": "<what you found>", "revision_notes": "<what you changed>"}}"""

# ---------------------------------------------------------------------------
# User prompt
# ---------------------------------------------------------------------------

USER_PROMPT_TEMPLATE = """\
BASE CV (context only — do not use as primary source):
---
{base_cv_yaml}
---

JOB LISTING:
---
{job_text}
---

TAILORED CV (PRIMARY SOURCE — use this for achievements and emphasis):
---
{tailored_cv_json}
---

GAP ANALYSIS (use to decide emphasis and partial-match handling):
---
{gap_diff_json}
---

USER NOTES (weave naturally if provided):
---
{user_notes}
---

Follow the PROCESS in the system instructions. Return ONLY valid JSON."""


# ---------------------------------------------------------------------------
# Pydantic output model
# ---------------------------------------------------------------------------


class CoverLetterOutput(BaseModel):
    """Pydantic model for the LLM cover letter generation response."""

    cover_letter_text: str
    self_critique: str  # What the model identified as AI-sounding
    revision_notes: str  # What was changed in revision pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_cover_letter(
    provider_model: str,
    base_cv: BaseCV,
    job_text: str,
    tailored_cv: TailoredCV,
    gap_diff: list[GapItem],
    user_notes: str = "",
    tone: str = "professional",
) -> str:
    """Generate a cover letter using the specified provider. Returns plain text.

    Args:
        provider_model: One of "claude-haiku", "claude-api", "gemini-flash", "openai".
        base_cv: The candidate's full base CV.
        job_text: The raw job listing text.
        tailored_cv: The tailored CV output (primary source for cover letter).
        gap_diff: Gap analysis items from CV tailoring.
        user_notes: Optional free-text notes to weave into the letter.
        tone: One of "formal", "professional", "confident", "direct", "casual".

    Returns:
        Plain text cover letter (paragraphs separated by blank lines).
    """
    base_cv_yaml = _serialize_base_cv(base_cv)
    tailored_cv_json = tailored_cv.model_dump_json(indent=2)
    gap_diff_json = json.dumps([g.model_dump() for g in gap_diff], indent=2)

    tone_instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["professional"])
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(tone_instruction=tone_instruction)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        base_cv_yaml=base_cv_yaml,
        job_text=job_text,
        tailored_cv_json=tailored_cv_json,
        gap_diff_json=gap_diff_json,
        user_notes=user_notes if user_notes else "(none)",
    )

    # Claude CLI: combine system + user into a single prompt (no chat turn support)
    if provider_model not in ("claude-api", "gemini-flash", "openai"):
        combined_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
        result = _invoke_with_retry(combined_prompt, CoverLetterOutput)
        return result.cover_letter_text

    # Chat-based providers: use system + user message pattern
    provider = get_provider(provider_model)
    last_exc: Exception | None = None

    for attempt in range(3):
        logger.info(
            "Cover letter attempt %d/3 via %s", attempt + 1, provider_model
        )
        effective_user = user_prompt
        if attempt > 0:
            logger.warning("Retrying cover letter — previous attempt failed: %s", last_exc)
            effective_user = (
                user_prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no commentary."
            )
        try:
            if provider_model == "gemini-flash":
                from google.genai import types as genai_types

                response = provider._client.models.generate_content(
                    model=provider._model,
                    contents=effective_user,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    ),
                )
                raw_text = response.text

            elif provider_model == "claude-api":
                response = provider._client.messages.create(
                    model=provider._model,
                    max_tokens=4000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": effective_user}],
                )
                raw_text = next(
                    (b.text for b in response.content if b.type == "text"), ""
                )

            elif provider_model == "openai":
                response = provider._client.chat.completions.create(
                    model=provider._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": effective_user},
                    ],
                )
                raw_text = response.choices[0].message.content

            else:
                raise RuntimeError(f"Unexpected provider_model in chat branch: {provider_model!r}")

            data = _extract_json(raw_text)
            result = CoverLetterOutput.model_validate(data)
            logger.info("Cover letter generation succeeded via %s", provider_model)
            return result.cover_letter_text

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Cover letter attempt %d failed: %s", attempt + 1, exc)

    raise RuntimeError(
        f"Cover letter generation failed after 3 attempts via {provider_model}. "
        f"Last error: {last_exc}"
    )
