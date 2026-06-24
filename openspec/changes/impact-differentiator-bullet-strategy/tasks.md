## 1. Models — Differentiator Fields on EvidenceMatch

- [x] 1.1 Add `differentiator_categories: list[str] = Field(default_factory=list)` to `EvidenceMatch` in `core/models.py` with docstring listing valid values
- [x] 1.2 Add `impact_signals: list[str] = Field(default_factory=list)` to `EvidenceMatch` in `core/models.py` with docstring listing valid values
- [x] 1.3 Add unit test in `tests/test_models.py` (or new test in `tests/test_pipeline.py`) verifying default values are empty lists, not None
- [x] 1.4 Add unit test verifying that two `EvidenceMatch` instances with defaults have independent list instances (no shared mutable state)
- [x] 1.5 Add unit test verifying existing `EvidenceMatch` construction without new fields still works

## 2. Bullet Strategy Prompt Rule

- [x] 2.1 Add `"bullet_strategy"` entry to `_RULES` dict in `core/pipeline.py` at level 0 covering: What + How + Result framing, depth signals, modern practices, ownership signals, role-weighted distribution (7-10 current, 5-7 past), ideal composition (50/30/20), generic-bullet avoidance, qualitative impact acceptance
- [x] 2.2 Resolve `bullet_strategy` in `_build_prompt()` via `_resolve_rule("bullet_strategy", level)` and inject into EXPERIENCE section (alongside keyword_policy_rule)
- [x] 2.3 Resolve `bullet_strategy` in `_build_system_prompt_for_chat()` and inject into EXPERIENCE section
- [x] 2.4 Resolve `bullet_strategy` in `generate_tailored_cv()` Stage 3 prompt and inject into EXPERIENCE section
- [x] 2.5 Verify `_resolve_rule("bullet_strategy", level)` returns the strategy text at all creativity levels (0-6)
- [x] 2.6 Add test class `TestBulletStrategyInPrompt` in `tests/test_pipeline.py` verifying strategy text appears in: single-shot prompt (all levels), chat system prompt, and Stage 3 generation prompt
- [x] 2.7 Verify key phrases in strategy text: "What + How + Result", "depth over exposure", "50% core skills", "ownership signals", "generic bullet", "role-weighted"

## 3. Stage 2 Prompt Extension — Differentiator Categories

- [x] 3.1 Extend `map_evidence()` prompt in `core/pipeline.py` to instruct model to populate `differentiator_categories` and `impact_signals` on each `EvidenceMatch`
- [x] 3.2 Include valid category labels in the prompt so the model knows which tags to use
- [x] 3.3 Include instruction to leave fields empty (default) when no differentiator applies
- [x] 3.4 Update the JSON schema in the Stage 2 prompt to include the new fields
- [x] 3.5 Add test in `tests/test_pipeline.py` verifying Stage 2 prompt contains `differentiator_categories` and `impact_signals` instructions
- [x] 3.6 Add test verifying mock Stage 2 output with populated differentiator fields is accepted

## 4. Generic-Bullet Validation

- [x] 4.1 Add `_GENERIC_PHRASE_RE` regex blacklist in `core/validation.py` for: "worked on", "responsible for", "helped with", "involved in", "collaborated with", "assisted with", "participated in", "supported" (as standalone verb), "handled", "was part of"
- [x] 4.2 Add `_OWNERSHIP_IMPACT_KEYWORDS` set in `core/validation.py` for density checking: incident, on-call, RCA, reduced, improved, automated, mentored, owned, led, designed, architected, saved, optimized, standardized, streamlined, eliminated, enabled, launched, migrated, scaled
- [x] 4.3 Add `_GENERIC_PATTERN_RE` regex in `core/validation.py` for common generic DevOps patterns: "Managed/Deployed/Configured [tool] [preposition]", "Set up [tool] for [purpose]", "Used [tool] to [verb]"
- [x] 4.4 Add `_check_generic_bullets(base, tailored, warnings)` function that:
  - Checks each bullet for generic phrases (warning if found)
  - Checks each bullet against generic DevOps patterns (warning if matched)
  - Checks each bullet for task-only pattern: short bullet + no numeric qualifier + no result keyword + no context phrase
  - Aggregates ownership/impact keyword density across all bullets (warning if < 20%)
- [x] 4.5 Call `_check_generic_bullets()` from `validate_tailored_cv()` unconditionally (no opt-in parameter — generic-bullet checks always run since they don't need JD keywords)
- [x] 4.6 Add test class `TestGenericBulletValidation` in `tests/test_validation.py`:
  - Task-only bullet triggers warning
  - Detailed bullet produces no generic warning
  - "worked on" phrase triggers warning
  - "Built" (active verb) produces no phrase warning
  - Generic DevOps pattern triggers warning
  - Rewritten specific bullet avoids pattern warning
  - Low ownership signal density triggers aggregate warning
  - Sufficient ownership signals avoid density warning
  - Case-insensitive generic-phrase matching
  - Word-boundary prevents false match ("networked on" not flagged)
  - Generic warnings coexist with keyword and metric warnings
  - `validate_tailored_cv()` without `jd_keywords` still runs generic checks

## 5. Tests — Model Defaults

- [x] 5.1 Add test in `tests/test_models.py` verifying `EvidenceMatch.model_validate({...})` without new fields produces `differentiator_categories=[]` and `impact_signals=[]`
- [x] 5.2 Add test verifying `EvidenceMatch.model_validate({...})` with new fields preserves them in output
- [x] 5.3 Add test verifying `EvidenceMap` with matches containing new fields serializes correctly

## 6. Integration and Polish

- [x] 6.1 Ensure all new code uses `from __future__ import annotations` where appropriate
- [x] 6.2 Ensure no new external dependencies
- [x] 6.3 Verify existing tests pass without modification (no regressions)
- [x] 6.4 Run full test suite: `uv run pytest tests/test_models.py tests/test_pipeline.py tests/test_validation.py -v`
- [x] 6.5 Review bullet strategy prompt text for conciseness (target: 15-25 lines, not bloating the prompt)
