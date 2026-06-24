## 1. Models — Placement Fields on EvidenceMatch

- [x] 1.1 Add `placement: str = "experience"` to `EvidenceMatch` in `core/models.py` (valid values: "experience", "skills", "omit")
- [x] 1.2 Add `placement_reason: str = ""` to `EvidenceMatch` in `core/models.py`
- [x] 1.3 Add unit tests in tests verifying default values and dict construction with new fields

## 2. Recruiter Plausibility Prompt Rule

- [x] 2.1 Add `"recruiter_plausibility"` entry to `_RULES` dict in `core/pipeline.py` at level 0 covering: truthful role-keyword placement, natural language, preserve stronger bullets, 1-2 keywords (3 only if related), placement distinction (experience/skills/omit)
- [x] 2.2 Resolve `recruiter_plausibility` in `_build_prompt()` and inject into EXPERIENCE section
- [x] 2.3 Resolve `recruiter_plausibility` in `_build_system_prompt_for_chat()` and inject
- [x] 2.4 Resolve `recruiter_plausibility` in `generate_tailored_cv()` Stage 3 prompt and inject
- [x] 2.5 Update `core_competencies` and `highlighted_technologies` rule text to clarify capability-vs-tool distinction
- [x] 2.6 Add test class `TestRecruiterPlausibilityInPrompt` in `tests/test_pipeline.py` verifying rule text in all prompt builders

## 3. Stage 2 Prompt Extension — Placement Fields

- [x] 3.1 Extend `map_evidence()` prompt to instruct model to populate `placement` and `placement_reason` on each `EvidenceMatch`
- [x] 3.2 Include valid placement values in the prompt instructions
- [x] 3.3 Update Stage 2 JSON schema to include `placement` and `placement_reason` fields
- [x] 3.4 Add test verifying Stage 2 prompt contains placement instructions
- [x] 3.5 Add test verifying mock Stage 2 output with placement fields is accepted

## 4. Keyword Placement Validation

- [x] 4.1 Add `_check_keyword_placement()` function in `core/validation.py` for suspicious role-keyword placement (tech in bullet but not in that role's technologies)
- [x] 4.2 Add `_check_awkward_chains()` function for noun-stack detection (3+ consecutive capitalized words)
- [x] 4.3 Add `_check_jd_mimicry()` function for JD-mimicry phrases (using SequenceMatcher bigram similarity)
- [x] 4.4 Add `_check_highlighted_tech_references()` for highlighted tech not in bullets
- [x] 4.5 Add `_check_role_tech_consistency()` for role technologies not in role bullets
- [x] 4.6 Add `_check_core_competencies_tool_leakage()` for concrete tools in core_competencies
- [x] 4.7 Call all new placement checks from `validate_tailored_cv()` (conditionally — mimicry needs JD text, others don't)
- [x] 4.8 Add test class `TestPlacementValidation` in `tests/test_validation.py` covering all 6 check types plus false-positive avoidance

## 5. Deterministic Technology Bolding

- [x] 5.1 Implement `apply_tech_bolding(tailored: TailoredCV) -> TailoredCV` in `core/pipeline.py`:
  - Collect techs from `highlighted_technologies` (global) and each role's `technologies` (per-role)
  - For each bullet, case-insensitive word-boundary regex replace tech names with `**tech**` (preserving original case)
  - Skip if already bolded (surrounded by `**`)
  - Resolve aliases (reuse `_KEYWORD_ALIASES` or inline)
  - Handle multi-word techs as phrases
- [x] 5.2 Call `apply_tech_bolding()` in `run_pipeline()` after `TailoredCV.model_validate()` and before validation
- [x] 5.3 Call `apply_tech_bolding()` in `run_pipeline_staged()` after Stage 3 generation and before validation
- [x] 5.4 Add test class `TestTechBolding` in `tests/test_pipeline.py`:
  - Single-word tech bolding
  - Multi-word tech bolding (e.g., "GitHub Actions")
  - Case-insensitive match
  - Word boundary prevents partial match
  - Already-bolded text preserved (no double-bolding)
  - Alias resolution (K8s → Kubernetes)
  - Global highlighted_technologies bolded in all roles
  - Role-specific technologies bolded only in their role
  - Bolding preserves original text structure
  - Bolding called in pipeline flow (mock test)

## 6. Tests — Fixtures and Integration

- [x] 6.1 Add suspicious JD fixture to `tests/conftest.py` with keywords: Jenkins, SonarQube, Nexus, IAM, SSO, OIDC, OAuth, VPN, DNS, routing
- [x] 6.2 Add base CV fixture with role-specific evidence (GitLab CI in one role, GitHub Actions in another)
- [x] 6.3 Add test for end-to-end pipeline flow with bolding applied
- [x] 6.4 Ensure all existing tests pass without modification

## 7. Integration and Polish

- [x] 7.1 Ensure no new external dependencies (all pure stdlib)
- [x] 7.2 Ensure `apply_tech_bolding()` does not block event loop (synchronous function, fast regex)
- [x] 7.3 Review recruiter plausibility prompt text for conciseness
- [x] 7.4 Run full test suite and confirm no regressions
