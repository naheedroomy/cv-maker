## Why

The current CV tailoring pipeline uses a single large prompt that performs gap analysis, CV rewriting, tailoring notes, and JSON output in one model call. While functional, this monolithic approach yields inconsistent keyword-to-evidence traceability and makes it difficult to enforce a disciplined natural-keyword embedding strategy (avoid stuffing, pair related keywords, embed only 1-2 per bullet, tie every keyword to concrete base-CV evidence). Splitting the pipeline into typed stages (requirement extraction → evidence mapping → CV generation) creates a verifiable chain from JD requirement through base-CV evidence to each tailored bullet, improving both quality and auditability.

## What Changes

- **Add prompt-level natural keyword embedding policy** in `core/pipeline.py`, shared across Claude CLI single-prompt and chat-provider system/user prompt flows. Defines rules: avoid keyword stuffing, identify key JD phrases, pair related keywords, 1-2 relevant keywords per experience bullet, every keyword backed by base-CV evidence and tied to a concrete action/outcome, do not dump keywords into skills.
- **Add deterministic keyword-stuffing validation** in `core/validation.py`. Lightweight, post-generation warnings (not hard failures) for suspicious patterns: repeated keyword reuse across bullets, excessive keyword density in a single bullet, skills-section keyword dumping, and unsubstantiated keywords lacking evidence trace.
- **Add regression tests** in `tests/test_pipeline.py` and `tests/test_validation.py` covering the new prompt rules, validation behavior, and keyword embedding policy enforcement.
- **Split the pipeline into typed stages** with Pydantic intermediate artifacts:
  - **Stage 1 — Requirement Extraction**: Parse JD into structured requirements (keyword phrases, category, tier, related phrases).
  - **Stage 2 — Evidence Mapping**: Map each requirement to exact base-CV evidence (match_level, source role/bullet/field, allowed keywords).
  - **Stage 3 — CV Generation**: Generate final `TailoredCV` using only base CV, requirements, evidence map, and keyword pairing plan. No raw JD text past stage 1.
- **Introduce new Pydantic models** (`JDRequirement`, `EvidenceMatch`, `KeywordPairingPlan`, `RequirementExtraction`, `EvidenceMap`) for intermediate artifacts. Keep existing `BaseCV`, `TailoredCV`, `GapItem` models stable.
- **Preserve existing hard constraints**: no contact/date/company/education/cert/language changes, keep role structure, no event-loop blocking, provider lazy imports, per-user keys, no UI scope.
- **Add test fixtures/evaluations** for JDs with 8-12 keyword phrases and base CVs with partially matching evidence, plus golden-file expected outputs for each pipeline stage.
- **No breaking changes** to the existing `BaseProvider.run()` interface or `run_pipeline()` signature — the single-prompt code path remains as a fallback.

## Capabilities

### New Capabilities

- `keyword-embedding-policy`: Prompt-level rules for natural keyword embedding in CV bullets. Avoids keyword stuffing, enforces 1-2 keywords per bullet, requires every keyword be backed by base-CV evidence and tied to a concrete action/outcome, pairs related keywords, and prevents dumping keywords into skills.
- `keyword-stuffing-validation`: Deterministic post-generation validation that detects suspicious keyword patterns (density violations, unsubstantiated keywords, skills-section dumping) and emits soft warnings without blocking generation.
- `multi-stage-pipeline`: Typed pipeline stages — Requirement Extraction (JD → structured requirements), Evidence Mapping (requirements → base CV evidence), CV Generation (evidence + requirements → TailoredCV). Each stage has its own Pydantic output model and the provider interface supports both single-shot and multi-stage modes.
- `pipeline-intermediate-models`: Pydantic v2 models for intermediate pipeline artifacts: `JDRequirement`, `EvidenceMatch`, `KeywordPairingPlan`, `RequirementExtraction`, `EvidenceMap`. These live in `core/models.py` alongside existing models.

### Modified Capabilities

<!-- None — no existing specs to modify. This is the first spec-driven change. -->

## Impact

- **`core/pipeline.py`**: New keyword policy rules in `_RULES` dict, applied via `_resolve_rule()`. New multi-stage pipeline functions (`extract_requirements()`, `map_evidence()`, `generate_tailored_cv()`) alongside existing `run_pipeline()`.
- **`core/validation.py`**: New `_check_keyword_stuffing()` soft-check function, integrated into `validate_tailored_cv()` warning flow.
- **`core/models.py`**: New Pydantic models for intermediate artifacts. Existing `BaseCV`, `TailoredCV`, `GapItem`, `TailoringNote`, `JobRequirements` unchanged.
- **`core/providers/base.py`**: New optional method `run_staged()` on `BaseProvider` for multi-stage mode. Existing `run()` interface unchanged.
- **`tests/test_pipeline.py`**: New test classes for keyword policy in prompts, multi-stage pipeline functions, prompt-level keyword rules across levels.
- **`tests/test_validation.py`**: New test class `TestKeywordStuffingValidation` for detection patterns, thresholds, and false-positive avoidance.
- **`tests/conftest.py`**: New fixtures for JD texts with 8-12 keyword phrases, partial-evidence base CVs, and golden expected outputs.
- **No changes to**: frontend, backend routes, LaTeX templates, Docker config, nginx, CI/CD, or any UI code.
