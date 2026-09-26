# PR #19 follow-up: evidence, voice calibration, and prompt-safety review

**Companion to:** [PR_19_COVER_LETTER_PROMPT_UPGRADE_REPORT.md](PR_19_COVER_LETTER_PROMPT_UPGRADE_REPORT.md)  
**Reviewed implementation:** merge commit `8a32130` (`core/cover_letter.py`, `core/cover_letter_audit.py`, `tests/test_cover_letter_prompt.py`, `tests/test_cover_letter_audit.py`)  
**Status:** Review and recommendations only; no prompt changes are implemented by this document.

## Decision

Retain the Conversational Storyteller architecture—flexible 3–4 paragraph narrative arc (~220–350 words), removal of clone few-shot templates, dynamic 6-tone matrix, and active engineering voice—but **clearly delineate prompt-level guidance from deterministic software gates**. The current automated tests verify template rendering, string presence, and regex pattern matching; they do not measure hiring manager response rates or guarantee that an arbitrary LLM will never hallucinate an ungrounded connection. Document the boundaries between generation, post-generation auditing, and candidate review.

## Findings and required changes

| Priority | Finding | Evidence | Change and acceptance criterion |
| --- | --- | --- | --- |
| P0 | **Lightweight audit is advisory, not an enforced gate.** The prompt instructs the LLM to avoid AI buzzwords, generic closings, and em dashes. If a model violates these instructions, `audit_cover_letter()` logs a warning to Python `logger.warning`, but the text is still committed to the database and returned to the candidate without UI warnings or a regeneration retry. | `core/cover_letter.py:157–167`; `backend/routers/cover_letter.py:94–105`; `core/cover_letter_audit.py:54–100`. | Clearly state in documentation that the regex scanner is an internal observability tool, not a blocking validation gate. If strict enforcement is desired in a future PR, add an optional retry pass or surface non-blocking warnings in the UI (`cover_letter_audit_warnings`). |
| P1 | **Writing sample vs. selected tone conflict resolution is unspecified.** The user prompt injects both a candidate's freeform `writing_sample` and a formal/conversational `tone_instruction`. If a candidate submits a casual writing sample but selects the `formal` tone, the model has no explicit tie-breaker or precedence rule. | `core/cover_letter.py:84, 186–218, 274–283`; `SYSTEM_PROMPT_TEMPLATE:84`. | Clarify in the prompt: `writing_sample` calibrates stylistic cadence, sentence variety, and vocabulary habits, while `tone` defines the social register, greeting, and sign-off. Ensure candidate review is emphasized when mixing disparate samples and tones. |
| P1 | **Self-critique and revision notes are ephemeral.** The Pydantic model `CoverLetterOutput` enforces `self_critique` and `revision_notes` from the LLM, but `backend/routers/cover_letter.py` discards them and only saves `cover_letter_text` into SQLite `jobs.cover_letter_text`. | `core/cover_letter.py:224–230`; `backend/routers/cover_letter.py:82–92`. | Document that `self_critique` and `revision_notes` intentionally function as "chain-of-thought scratchpads" to improve generation quality without bloating the database. If user-facing audit logs are desired later, add corresponding database columns (`cover_letter_critique_json`). |
| P1 | **Partial match framing requires verified adjacent architecture.** The prompt encourages candidates to bridge partial matches by citing equivalent architectures (e.g. AWS/ArgoCD translating to GCP/GKE). If a candidate has neither tool in their base CV, a model could extrapolate an equivalence that is ungrounded. | `core/cover_letter.py:130–136`; original report §3.1. | Reinforce in prompt guidelines: equivalent tool assertions must have verified evidence for the source tool in the base CV. Remind candidates to confirm all architectural translations before sending. |
| P2 | **String-matching tests do not evaluate output quality or voice.** The new test suite in `tests/test_cover_letter_prompt.py` asserts dictionary key presence, string formatting without exceptions, and mock provider calls. It does not evaluate live LLM generation across varied real-world resumes and job postings. | `tests/test_cover_letter_prompt.py:65–144`. | Distinguish unit-level template safety tests from live empirical evaluations. Recommend building a consent-safe regression fixture set to qualitatively review live generation outputs across Claude, Gemini, and OpenAI. |
| P2 | **Tone hints in frontend vs. system prompt directives.** The frontend `ToneSelector.vue` provides short user hints (`"Like emailing a friend at the company, punchy and real"`), while `_TONE_INSTRUCTIONS` in the backend provides deeper narrative guidance. | `frontend/src/components/ToneSelector.vue:13–20`; `core/cover_letter.py:19–55`. | Keep the frontend hints concise for UX, but ensure semantic consistency so user expectations match the prompt's behavioral output. |

## Suggested replacement for the report's outcome claims

> PR #19 overhauls cover letter generation by replacing mechanical word and sentence quotas with a 4-stage narrative arc (~220–350 words, 3–4 paragraphs), dynamic 6-tone voice directives, positive writing craft principles, and strict factual grounding. Automated tests verify prompt template safety, schema validation, and regex audit coverage. The system does not guarantee interview shortlisting, nor does it deterministically prevent all LLM variance. Candidates remain the final editor and must verify that the letter accurately represents their experience, voice, and intentions before submitting an application.

## Verification plan for follow-up testing

1. **Consent-Safe Golden Fixture Suite**:
   - Construct 3 standard test cases:
     - **Senior Platform Engineer**: Rich metrics, multi-cloud experience, applying to high-scale streaming platform.
     - **Mid-Level Full-Stack Developer**: Light on metrics, career transition, partial match on database stack.
     - **Junior / Career Switcher**: Non-traditional background, strong project evidence, applying to startup with no formal hiring manager listed.
2. **Multi-Model Regression Comparison**:
   - Run the golden fixtures across `claude-api` (Claude 3.5 Sonnet), `gemini-flash` (Gemini 2.5 Flash), and `openai` (GPT-4o).
   - Evaluate outputs blind for:
     - Length adherence (220–350 words, 3–4 paragraphs).
     - Absence of prohibited AI vocabulary (*delve, tapestry, pivotal, testament, seamless*).
     - Presence of genuine context hook vs. generic corporate praise.
     - Factual grounding (zero hallucinated tools or phantom metrics).
3. **Observability Verification**:
   - Verify that when an LLM emits an em dash or AI vocabulary, `core/cover_letter_audit.py` captures and logs the warning cleanly in backend telemetry without raising an uncaught exception.

## Local verification status

- **Unit & Integration Tests**: `uv run pytest` → **258 passed, 5 skipped, 0 failures** across all 263 tests.
- **Linting Compliance**: `uv run ruff check core/cover_letter.py tests/test_cover_letter_prompt.py tests/test_cover_letter_audit.py` → **All checks passed (0 errors)**.
- **Frontend Typecheck & Build**: `cd frontend && npm run build` → **Passed in 212ms** with 0 errors.
- **Git Status**: Report files remain uncommitted in working tree as requested.
