"""Cover letter generation — prompt builder, Pydantic model, and provider-agnostic generation."""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel

from cv_maker.models import BaseCV, GapItem, TailoredCV
from cv_maker.pipeline import _extract_json, _invoke_with_retry, _serialize_base_cv
from cv_maker.providers import get_provider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tone instructions — parameterized prompt fragments (per D-04)
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
    "casual": (
        "Write conversationally. Show personality. Use contractions. "
        "OK to use informal transitions and first person naturally."
    ),
}

# ---------------------------------------------------------------------------
# Anti-AI writing rules — baked into the prompt (per D-05)
# ---------------------------------------------------------------------------

ANTI_AI_RULES = """
ANTI-AI WRITING RULES (mandatory -- violations will be caught in the self-critique step):

1. NO SIGNIFICANCE INFLATION: Never use "pivotal", "testament to", "underscores",
   "crucial role", "shaping the future of". Say what happened, not how important it was.
   BAD: "This role is a pivotal opportunity to shape the future of cloud infrastructure."
   GOOD: "You need someone to migrate 200 services to Kubernetes. I did that at Sysco."

2. NO PROMOTIONAL LANGUAGE: Never use "passionate about", "thrilled to apply",
   "committed to excellence", "vibrant", "showcase". These are AI tells.
   BAD: "I am passionate about cloud-native technologies and thrilled to apply."
   GOOD: "I like building things that stay up. Kubernetes and I get along."

3. SIMPLE VERBS: "I connect X and Y" not "I serve as the bridge between X and Y".
   "I built" not "I spearheaded the development of". "I fixed" not "I addressed challenges in".
   BAD: "I spearheaded the development of a comprehensive observability platform."
   GOOD: "I built the observability platform -- Datadog dashboards, alert routing, the whole stack."

4. NO RULE-OF-THREE CLUSTERS: Never list three abstract nouns together.
   BAD: "innovation, collaboration, and impact"
   GOOD: Pick one. Be specific about it.

5. NO GENERIC CONCLUSIONS: Never write "I look forward to the opportunity to discuss"
   or "I would welcome the chance to contribute". End with something specific.
   BAD: "I look forward to discussing how I can contribute to your team."
   GOOD: "Happy to walk through the K8s migration timeline -- my calendar's open."

6. NO -ING PARTICIPIAL PADDING: Never tack on "leveraging", "contributing to",
   "fostering", "showcasing", "emphasizing". These are AI fluff.
   BAD: "...leveraging my expertise in cloud infrastructure, contributing to team success."
   GOOD: Cut it. The sentence was done before the -ing phrase.

7. NO FILLER: "To" not "In order to". "I can" not "I have the ability to".
   "Because" not "Due to the fact that".
   BAD: "In order to ensure the reliability of the system, I have the ability to implement monitoring."
   GOOD: "To keep the system reliable, I wire up monitoring."

8. VARY SENTENCE RHYTHM: Mix short punchy sentences with longer ones.
   Not every sentence should be 15-20 words. Some should be 5. Some 30.
   BAD: "I have extensive experience with Kubernetes and have worked on many clusters at scale."
   GOOD: "I've run Kubernetes at scale. Three clusters, 340 pods, two years of on-call at Sysco."

9. HAVE OPINIONS, DON'T HEDGE: "I can" not "I could potentially be able to".
   "This is a good fit" not "I believe this could potentially be a good fit".
   BAD: "I believe I could potentially be a good fit for this role."
   GOOD: "This role fits. You want a platform engineer who's shipped GitOps at scale -- I have."

10. SPECIFICITY OVER SCOPE: Concrete facts, not broad claims.
    BAD: "I have extensive experience in cloud infrastructure."
    GOOD: "I ran 340 pods across 3 clusters at Sysco Labs for 2 years."
"""


# ---------------------------------------------------------------------------
# Pydantic output model
# ---------------------------------------------------------------------------


class CoverLetterOutput(BaseModel):
    """Pydantic model for the LLM cover letter generation response."""

    cover_letter_text: str
    self_critique: str  # What the model identified as AI-sounding
    revision_notes: str  # What was changed in revision pass


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def _build_cover_letter_prompt(
    base_cv_yaml: str,
    job_text: str,
    tailored_cv_json: str,
    gap_diff_json: str,
    user_notes: str,
    tone: str,
) -> tuple[str, str]:
    """Build system and user prompts for cover letter generation.

    Returns:
        (system_prompt, user_prompt) tuple for chat-based providers.
        For Claude CLI, combine them into a single prompt.
    """
    tone_instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["professional"])

    system_prompt = f"""\
You are writing a cover letter for a job application. You have access to:
1. The candidate's base CV (full background)
2. The job listing
3. The tailored CV (already optimized for this role) — this is your PRIMARY source
4. The gap analysis (what matched, what's missing)
5. User notes (specific things to mention)

TONE: {tone_instruction}

{ANTI_AI_RULES}

PROCESS (execute all steps internally, return only the final JSON):
STEP 1: Write a 3-4 paragraph cover letter draft using the tailored CV as your primary source.
        The tailored CV is your PRIMARY source. The gap analysis tells you what to emphasize.
        The base CV is context only -- do NOT use it as the primary source.
        If user notes are provided, weave them naturally into the letter.
STEP 2: You are now a hostile AI-detection reviewer. Read your draft and find at least 3 AI tells.
        Check every sentence against the 10 anti-AI rules above. If you find fewer than 3 issues,
        you are not looking hard enough.
STEP 3: Rewrite the draft to fix every issue found. The final version must pass the anti-AI review.
STEP 4: Return ONLY valid JSON (no markdown fences):
{{"cover_letter_text": "<final revised text>", "self_critique": "<what you found>", "revision_notes": "<what you changed>"}}"""

    user_prompt = f"""\
BASE CV (context only -- do not use as primary source):
---
{base_cv_yaml}
---

JOB LISTING:
---
{job_text}
---

TAILORED CV (PRIMARY SOURCE -- use this for achievements and emphasis):
---
{tailored_cv_json}
---

GAP ANALYSIS (use this to know what to emphasize):
---
{gap_diff_json}
---

USER NOTES (weave naturally if provided):
---
{user_notes if user_notes else "(none)"}
---

Follow the PROCESS in the system instructions. Return ONLY valid JSON."""

    return system_prompt, user_prompt


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
        tone: One of "formal", "professional", "confident", "casual".

    Returns:
        Plain text cover letter (paragraphs separated by blank lines).
    """
    base_cv_yaml = _serialize_base_cv(base_cv)
    tailored_cv_json = tailored_cv.model_dump_json(indent=2)
    gap_diff_json = json.dumps([g.model_dump() for g in gap_diff], indent=2)

    system_prompt, user_prompt = _build_cover_letter_prompt(
        base_cv_yaml=base_cv_yaml,
        job_text=job_text,
        tailored_cv_json=tailored_cv_json,
        gap_diff_json=gap_diff_json,
        user_notes=user_notes,
        tone=tone,
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
