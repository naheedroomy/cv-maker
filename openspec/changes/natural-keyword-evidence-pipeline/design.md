## Context

The CV tailoring pipeline (`core/pipeline.py`) currently uses a single large prompt that performs gap analysis, CV rewriting, tailoring notes, and JSON output in one model call. The prompt is built by `_build_prompt()` (Claude CLI single-shot) and `_build_system_prompt_for_chat()` + `_build_user_prompt()` (chat providers). Both use a centralized `_RULES` dict with creativity-level thresholds resolved via `_resolve_rule()`.

Post-generation validation (`core/validation.py`) checks hard invariants (contact, dates, companies, certifications, languages) and soft warnings (invented metrics). There is currently no keyword-discipline validation.

All providers implement `BaseProvider.run(base_cv, job_text, creativity_level, user_notes) -> tuple[TailoredCV, list[GapItem]]`. The `BackendWorker` calls `run_pipeline()` or the provider's `run()` in `asyncio.to_thread()`.

The existing models (`core/models.py`) include `BaseCV`, `TailoredCV`, `GapItem`, `TailoringNote`, `JobRequirements` — all Pydantic v2.

Constraints:
- No contact/date/company/education/cert/language changes (hard invariants in `validation.py`)
- Keep role structure (same number of experience entries, same companies, same dates)
- No event-loop blocking (all AI calls in `asyncio.to_thread()`)
- Provider lazy imports (no module-scope imports in `core/providers/__init__.py`)
- Per-user API keys resolved at runtime via `backend.settings_cache`
- No UI scope

## Goals / Non-Goals

**Goals:**
1. Add a prompt-level natural keyword embedding policy as a new rule in `_RULES`, applied at all creativity levels in both `_build_prompt()` and `_build_system_prompt_for_chat()`.
2. Add lightweight deterministic keyword-stuffing validation warnings in `core/validation.py` — no hard failures, no external dependencies, pure regex/text analysis.
3. Add comprehensive regression tests for the keyword policy in prompts and validation behavior.
4. Introduce a multi-stage pipeline (`extract_requirements()`, `map_evidence()`, `generate_tailored_cv()`) with Pydantic intermediate artifacts, with the single-shot path preserved as the default.
5. Define `JDRequirement`, `EvidenceMatch`, `KeywordPairingPlan`, `RequirementExtraction`, `EvidenceMap` models in `core/models.py`.
6. Extend `BaseProvider` with an optional `run_staged()` method, keeping `run()` unchanged.
7. Add test fixtures for JDs with 8-12 keyword phrases and base CVs with partial evidence, plus golden expected outputs.

**Non-Goals:**
- No UI changes (frontend stays unchanged).
- No database schema changes.
- No changes to backend routes, worker lifecycle, or SSE events.
- No changes to LaTeX rendering or templates.
- No changes to the existing `GapItem` or `TailoredCV` model schemas.
- No breaking changes to `BaseProvider.run()` or `run_pipeline()` signatures.
- No external keyword-extraction libraries (NLP, embeddings, etc.) — everything is prompt-driven + deterministic checks.

## Decisions

### Decision 1: Keyword policy as a new `_RULES` entry

**Choice**: Add a `"keyword_policy"` key to the existing `_RULES` dict, resolved at level 0 (applies at all creativity levels), and include it in both prompt builders.

**Rationale**: The `_RULES` mechanism is proven, tested, and used by every concern (titles, bullets, skills, inference, anti-fabrication, etc.). Adding keyword policy here ensures it propagates to all provider paths and creativity levels without duplicating logic. The policy is a formatting/discipline rule, not a content-generation rule, so it makes sense to apply at level 0.

**Alternatives considered**:
- Hard-coding in prompt builders: rejected because it would need duplication across `_build_prompt()`, `_build_system_prompt_for_chat()`, and any future prompt builders.
- Separate module: overkill for a prompt rule that is 5-10 lines of text.

### Decision 2: Deterministic validation without NLP dependencies

**Choice**: Use regex-based and text-analysis checks for keyword stuffing detection. No spaCy, NLTK, or embedding-based similarity.

**Rationale**: The project has no NLP dependencies and adding them for soft warnings is disproportionate. The checks are intentionally loose — they flag suspicious patterns for human review, not block generation. Simple heuristics (keyword count per bullet, repeated keyword across bullets, bare-technology-list detection) catch 80%+ of stuffing cases with zero runtime cost.

**Alternatives considered**:
- Embedding similarity between JD keywords and bullet text: accurate but requires a sentence-transformer model (~500MB download, significant latency per validation call). Overkill for soft warnings.
- LLM-based validation: would require another model call, doubling cost and latency.

### Decision 3: Staged pipeline as additive, not replacement

**Choice**: Keep `run_pipeline()` as the default single-shot path. Add new functions `extract_requirements()`, `map_evidence()`, `generate_tailored_cv()` alongside it. Add `run_staged()` on providers as optional.

**Rationale**: Backward compatibility is critical — existing tests, the worker, and any external callers of `run_pipeline()` must not break. The staged pipeline is an opt-in improvement for providers that support it well (Claude API, GPT-4) while Claude CLI and Gemini stay single-shot until proven reliable in multi-turn.

**Alternatives considered**:
- Replace `run_pipeline()` entirely: rejected because many providers may not handle multi-turn reliably, and the single-shot path is simpler and faster for quick tailoring.
- Separate module: would fragment pipeline logic and duplicate the `_RULES`/prompt-building infrastructure.

### Decision 4: Intermediate models in `core/models.py`

**Choice**: Add `JDRequirement`, `EvidenceMatch`, `KeywordPair`, `KeywordPairingPlan`, `RequirementExtraction`, `EvidenceMap` to the existing `core/models.py`.

**Rationale**: All models live in one file per the project's established pattern. No circular import risk — these models don't import from providers or pipeline. Pydantic v2 features (field validators, model validators) are already in use.

**Alternatives considered**:
- `core/pipeline_models.py`: would add a new import path and deviate from the existing convention.
- Dataclasses: rejected because the existing codebase uses Pydantic v2 consistently, and these models will be serialized to JSON for prompt context.

### Decision 5: Keyword matching aliases and stemming

**Choice**: Maintain a simple alias map for known abbreviations (e.g., "K8s" → "Kubernetes", "GH Actions" → "GitHub Actions") and use Python's built-in string methods for case-insensitive matching. No external stemming library.

**Rationale**: The alias map covers the most common tech abbreviations relevant to CV tailoring. Adding `nltk.stem` or `PorterStemmer` for simple suffix stripping is disproportionate — a small set of suffix rules (strip "ing", "ed", "s", "ment") handled inline suffices for soft warnings.

### Decision 6: Stage 3 does NOT receive raw JD text

**Choice**: Stage 3 (CV Generation) receives only the structured `RequirementExtraction`, `EvidenceMap`, and `KeywordPairingPlan` — not the raw JD string.

**Rationale**: This is the core architectural benefit of the split: Stage 3 cannot "cheat" by re-reading the JD and keyword-stuffing. It must work from the curated evidence map, which enforces one-requirement-to-one-evidence traceability. If the evidence map says a keyword has "missing" evidence, Stage 3 cannot embed it.

## Risks / Trade-offs

- **[Risk] Increased latency from 3 model calls instead of 1**: Each stage is a separate provider call. In worst case, this triples end-to-end latency.
  → **Mitigation**: Stage 1 is fast (structured extraction, small output). Stage 2 is deterministic and ideally model-free. The real cost is Stage 3. Also, the single-shot path remains available as the default; staged is opt-in.

- **[Risk] Provider JSON reliability for intermediate artifacts**: Not all providers reliably produce structured JSON. Gemini Flash and Claude CLI may return non-JSON or malformed output for `JDRequirement` lists.
  → **Mitigation**: Reuse the existing `_extract_json()` + `_invoke_with_retry()` pattern. The `_RULES` prompt-based approach (telling the model the schema inline) has proven effective for `TailoredCV` — same technique for intermediate models.

- **[Risk] Over-constraining bullets reduces natural writing quality**: Strict keyword limits (max 2 per bullet) might force awkward bullet construction or omission of genuinely relevant content.
  → **Mitigation**: The keyword policy is prompt-level guidance, not post-generation enforcement. Validation emits soft warnings, not hard failures. A bullet with 3 keywords may still be valid; the warning just flags it for review. The "must be tied to an action/outcome" rule is the real quality gate.

- **[Risk] Keyword-stuffing validation false positives**: Legitimate bullets (e.g., listing technologies for a role's "technologies" section, or a bullet that naturally references several tools in a workflow) may trigger warnings.
  → **Mitigation**: Warnings are informational only — they do not block generation or surface to end users unless the UI chooses to display them. Thresholds are conservative (3+ keywords to trigger, 4+ bullets to flag reuse).

- **[Risk] Stage 2 (Evidence Mapping) complexity**: Deterministically mapping JD keywords to base-CV bullet indices is non-trivial without semantic understanding.
  → **Mitigation**: Stage 2 is implemented as a model call (not pure regex), using the same prompt-based approach. The model receives the requirement list and the full base CV and is asked to produce the `EvidenceMap` JSON. This is the most expensive stage but the most critical for quality.

- **[Trade-off] No backward incompatibility with existing tests**: All existing tests pass unchanged because new code is additive. However, the multi-stage pipeline functions have their own test suite, and the keyword policy embedded in single-shot prompts may subtly alter LLM behavior. Golden-file tests with mock provider outputs isolate this concern.
