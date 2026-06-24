## 1. Models — Intermediate Pipeline Artifacts

- [x] 1.1 Add `JDRequirement` model to `core/models.py` with fields: phrase, category (Literal), tier (int 1-3, validated), related_phrases (list[str]), description (str)
- [x] 1.2 Add `EvidenceMatch` model to `core/models.py` with fields: requirement_phrase, match_level (Literal), source_company, source_role, source_bullet_index, source_field, evidence_text, allowed_keywords (list[str]), inference_rule
- [x] 1.3 Add `KeywordPair` model to `core/models.py` with fields: keywords (list[str]), rationale, evidence_source, suggested_bullet_count
- [x] 1.4 Add `KeywordPairingPlan` model to `core/models.py` with field: pairs (list[KeywordPair])
- [x] 1.5 Add `RequirementExtraction` model to `core/models.py` with fields: requirements (list[JDRequirement]), raw_jd_hash (str), model_metadata (dict)
- [x] 1.6 Add `EvidenceMap` model to `core/models.py` with fields: matches (list[EvidenceMatch]), pairing_plan (KeywordPairingPlan), coverage_summary (dict), base_cv_hash (str)
- [x] 1.7 Add unit tests for all new models in `tests/test_models.py` (or a new test class in `tests/test_pipeline.py`): validation, serialization, tier clamping, category enum

## 2. Keyword Embedding Policy in Prompts

- [x] 2.1 Add `"keyword_policy"` entry to `_RULES` dict in `core/pipeline.py` at level 0 with the natural keyword embedding rules (max 1-2 per bullet, pair related keywords, evidence-backed, no skills dumping, tie to action/outcome)
- [x] 2.2 Resolve `keyword_policy` in `_build_prompt()` via `_resolve_rule("keyword_policy", level)` and inject into the prompt output (experience section or standalone KEYWORD POLICY block)
- [x] 2.3 Resolve `keyword_policy` in `_build_system_prompt_for_chat()` and inject into the system prompt
- [x] 2.4 Add test class `TestKeywordPolicyInPrompt` in `tests/test_pipeline.py` verifying keyword policy text appears in prompts at all creativity levels (0-6), in both `_build_prompt()` and `_build_system_prompt_for_chat()`
- [x] 2.5 Verify keyword policy text includes key phrases: "1-2 relevant keywords per bullet", "every keyword backed by base-CV evidence", "tied to a concrete action/outcome", "do not dump keywords into skills"

## 3. Keyword-Stuffing Validation

- [x] 3.1 Add alias map constant `_KEYWORD_ALIASES` in `core/validation.py` for known tech abbreviations (e.g., "K8s" → "Kubernetes", "GH Actions" → "GitHub Actions")
- [x] 3.2 Add `_normalize_keyword()` helper that lowercases, strips punctuation, resolves aliases, and applies simple suffix stemming (strip "ing", "ed", "s", "ment")
- [x] 3.3 Add `_check_keyword_stuffing(base, tailored, jd_keywords, warnings)` function that:
  - Counts distinct JD keywords per bullet (warning if 3+)
  - Detects bare keyword-list bullets (comma-separated tech enumeration without action verbs)
  - Detects keyword reuse across 4+ bullets
  - Detects unsubstantiated keywords in skills section
- [x] 3.4 Expose `jd_keywords` parameter: `validate_tailored_cv()` gains optional `jd_keywords: list[str] | None = None`. When None, keyword checks are skipped (backward compat). When provided, keyword checks run.
- [x] 3.5 Add test class `TestKeywordStuffingValidation` in `tests/test_validation.py`:
  - Bullet with 3+ keywords triggers warning
  - Bullet with 0-2 keywords produces no keyword warning
  - Bare technology list triggers warning
  - Action-verb bullet with keywords produces no keyword warning
  - Unsubstantiated skill triggers warning
  - Verified skill produces no keyword warning
  - Keyword overuse (4+ bullets) triggers warning
  - Case-insensitive matching
  - Alias resolution (K8s → Kubernetes)
  - Stem-based matching (deploying → deploy)
  - No keyword warnings when `jd_keywords=None`

## 4. Multi-Stage Pipeline Functions

- [x] 4.1 Add `extract_requirements(job_text: str, provider_fn, cli_model: str = "") -> RequirementExtraction` in `core/pipeline.py` — builds a prompt instructing the model to parse JD into structured requirements, calls provider, returns `RequirementExtraction`
- [x] 4.2 Add `map_evidence(requirements: RequirementExtraction, base_cv: BaseCV, provider_fn, creativity_level: int = 2) -> EvidenceMap` in `core/pipeline.py` — sends requirements + base CV to model, returns evidence map with match levels, source references, allowed keywords, and keyword pairing plan
- [x] 4.3 Add `generate_tailored_cv(base_cv: BaseCV, requirements: RequirementExtraction, evidence_map: EvidenceMap, provider_fn, creativity_level: int = 2, user_notes: str = "") -> TailoredCV` in `core/pipeline.py` — builds prompt from structured inputs only (no raw JD), produces final `TailoredCV`
- [x] 4.4 Add `run_pipeline_staged(base_cv: BaseCV, job_text: str, provider_fn, creativity_level: int = 2, cli_model: str = "", user_notes: str = "") -> tuple[TailoredCV, list[GapItem]]` — orchestrates all three stages sequentially, runs post-generation validation, returns same type as `run_pipeline()`
- [x] 4.5 Build prompts for each stage using the existing pattern: embed structured data as YAML/JSON in the prompt, include the JSON schema for the expected output, and describe the task precisely
- [x] 4.6 Reuse `_extract_json()` and `_invoke_with_retry()` patterns for all three stages
- [x] 4.7 Run `validate_tailored_cv()` after Stage 3, log warnings

## 5. Provider Interface Extension

- [x] 5.1 Add optional `run_staged()` method to `BaseProvider` abstract class (not abstract — default raises NotImplementedError or delegates to `run()`)
- [x] 5.2 Implement `run_staged()` on at least one provider (recommended: `ClaudeAPIProvider` since it has reliable JSON mode) by calling `run_pipeline_staged()` with the provider's own call function
- [x] 5.3 Ensure `run()` on all providers continues to work identically (no signature changes)
- [x] 5.4 Add `provider_fn` parameter pattern: a callable that accepts a prompt string and returns raw text, so `run_pipeline_staged()` is provider-agnostic (works with CLI `_invoke_claude` or any provider's internal call method)

## 6. Tests — Multi-Stage Pipeline

- [x] 6.1 Add JD fixture with 8-12 keyword phrases to `tests/conftest.py` (e.g., `jd_with_keywords` fixture: a realistic JD text with explicit technology and responsibility keywords)
- [x] 6.2 Add partial-evidence base CV fixture to `tests/conftest.py` (`base_cv_partial_evidence`: a BaseCV that has evidence for ~60% of the JD keywords, partial for ~20%, missing for ~20%)
- [x] 6.3 Add golden fixture for expected `RequirementExtraction` output (`expected_requirements` fixture)
- [x] 6.4 Add golden fixture for expected `EvidenceMap` output (`expected_evidence_map` fixture)
- [x] 6.5 Add test class `TestMultiStagePipeline` in `tests/test_pipeline.py`:
  - `extract_requirements()` with mocked provider returns valid `RequirementExtraction`
  - `map_evidence()` with mocked provider returns valid `EvidenceMap` with correct match levels
  - `generate_tailored_cv()` with mocked provider returns valid `TailoredCV`
  - `run_pipeline_staged()` orchestration returns `(TailoredCV, list[GapItem])`
  - End-to-end: mock all provider calls, verify `run_pipeline_staged()` output matches golden expected CV
  - `run_pipeline_staged()` applies post-generation validation and returns warnings
- [x] 6.6 Add test class `TestMultiStagePromptContent` in `tests/test_pipeline.py`:
  - Stage 1 prompt contains JD text and schema for `RequirementExtraction`
  - Stage 2 prompt contains requirement list and base CV YAML, schema for `EvidenceMap`
  - Stage 3 prompt does NOT contain raw JD text (negative assertion)
  - Stage 3 prompt contains evidence map summary and keyword pairing plan
- [x] 6.7 Add test class `TestStagedPipelineBackwardCompat` in `tests/test_pipeline.py`:
  - All existing `run_pipeline()` tests pass unchanged
  - `run_pipeline()` still works with keyword policy embedded in prompt
  - `run_pipeline()` and `run_pipeline_staged()` return same type signature

## 7. Tests — Keyword Policy and Validation Integration

- [x] 7.1 Verify `_build_prompt()` at level 2 includes keyword policy section in prompt text
- [x] 7.2 Verify `_build_system_prompt_for_chat()` at level 2 includes keyword policy section
- [x] 7.3 Verify keyword policy text is consistent across single-shot and multi-stage prompts
- [x] 7.4 Test that `validate_tailored_cv()` with `jd_keywords` parameter detects keyword stuffing in a tailored CV that violates the policy
- [x] 7.5 Test that `validate_tailored_cv()` without `jd_keywords` parameter (default None) does NOT run keyword checks (backward compat)
- [x] 7.6 Test that keyword warnings are appended to the warnings list alongside existing invented-metric warnings (not replacing them)

## 8. Integration and Polish

- [x] 8.1 Ensure all new code uses `from __future__ import annotations` where appropriate
- [x] 8.2 Ensure no new external dependencies are introduced (keyword validation is pure Python stdlib + existing deps)
- [x] 8.3 Verify provider lazy imports are preserved — `core/models.py` does not import any provider module
- [x] 8.4 Verify `run_pipeline_staged()` does not block the event loop — all provider calls go through `asyncio.to_thread()` in the worker (pipeline functions themselves are sync; the worker wraps them)
- [x] 8.5 Run existing test suite to confirm no regressions: `uv run pytest tests/test_pipeline.py tests/test_validation.py -v`
- [x] 8.6 Review keyword policy text for clarity and conciseness — the prompt is already very large (~2000 words); the keyword policy addition should be 5-10 lines maximum
