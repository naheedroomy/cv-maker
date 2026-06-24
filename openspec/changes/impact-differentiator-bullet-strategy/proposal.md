## Why

Many DevOps/cloud/platform engineering resumes look identical because candidates copy successful templates and reuse generic bullet wording ("Built CI/CD pipelines with Jenkins," "Managed Kubernetes deployments," "Provisioned infrastructure with Terraform"). These task-only bullets fail to differentiate the candidate — they describe what was done, not why it mattered, how well it was done, or what higher-order skills were demonstrated. The current CV tailoring pipeline produces well-structured, keyword-compliant output but does not encode recruiter-aware differentiator strategies: impact framing (What + How + Result), depth signals (reusable modules, standardization, multi-environment experience), modern practice highlighting (GitOps, platform engineering, DevSecOps, cost optimization), ownership signals (incident response, production ownership, mentorship), and role-weighted bullet distribution (7-10 detailed bullets for current role, 5-7 simpler bullets for past roles). This change encodes these strategies as prompt rules, validation checks, and optional evidence-map fields so that every tailored CV reads as a high-signal, differentiated document rather than a generic keyword-matched template.

## What Changes

- **Add impact/differentiator bullet strategy prompt rule** as a new `"bullet_strategy"` entry in `_RULES` in `core/pipeline.py`, resolved at level 0 (applies at all creativity levels). Injected into single-shot prompt, chat system prompt, and Stage 3 generation prompt. Covers: What + How + Result framing, depth signals, modern practice cues, role-weighted bullet counts (7-10 current, 5-7 past), ideal bullet composition (50% core skills, 30% advanced differentiators, 20% ownership/leadership), ownership signals (incident response, cost optimization, security, mentorship), and a generic-bullet avoidance directive.
- **Add deterministic generic-bullet validation** in `core/validation.py` as soft warnings. Detects bullets that are task+tool only (no specificity, context, result, or differentiator), bullets using overused generic phrases ("worked on", "responsible for", "helped with", "involved in", "collaborated with"), and bullets lacking any ownership/impact/leadership signal. Warnings only — never hard failures.
- **Add optional `differentiator_categories` field** to `EvidenceMatch` model in `core/models.py` — a list of category labels (e.g. "cost_optimization", "security", "mentorship", "platform_engineering", "incident_response", "automation", "observability") that the evidence mapping stage can attach when the base CV substantiates a differentiator. Non-breaking: defaults to empty list.
- **Add optional `impact_signals` field** to `EvidenceMatch` — a list of qualitative impact tags (e.g. "reduced_latency", "improved_consistency", "standardized_process", "automated_workflow") for evidence that demonstrates impact even without numeric metrics. Non-breaking: defaults to empty list.
- **Extend the staged Stage 2 (Evidence Mapping) prompt** to request differentiator categories and impact signals alongside existing match data. The prompt instructs the model to identify evidence-supported differentiators.
- **Add regression tests** in `tests/test_pipeline.py` (bullet strategy in prompts, differentiator fields in evidence map), `tests/test_validation.py` (generic bullet detection patterns, false-positive avoidance), and `tests/test_models.py` (optional field defaults).
- **No breaking changes** to existing models, provider interface, or `run_pipeline()`. All new optional fields default to empty collections.
- **No UI/frontend/backend route changes, no external dependencies, no fabricated metrics.**

## Capabilities

### New Capabilities

- `impact-bullet-strategy`: Prompt-level rules governing how CV bullets should be written to maximize recruiter impact. Encodes What + How + Result framing, depth-over-exposure signals, role-weighted distribution, ideal composition ratios, ownership/leadership cues, and generic-bullet avoidance. Applied across all provider paths and creativity levels.
- `generic-bullet-validation`: Deterministic soft validation that flags bullets lacking substance — task-only bullets without specificity, bullets using weak/generic phrasing, and bullets missing any ownership/impact signal. Warnings only, integrated into existing `validate_tailored_cv()` flow.
- `differentiator-categories`: Optional fields on `EvidenceMatch` (`differentiator_categories`, `impact_signals`) that the evidence mapping stage populates when base-CV evidence supports recruiter-valued differentiators. Defaults to empty, fully backward compatible.

### Modified Capabilities

<!-- None — this is a new change building on natural-keyword-evidence-pipeline. -->

## Impact

- **`core/pipeline.py`**: New `"bullet_strategy"` rule in `_RULES`, resolved in `_build_prompt()`, `_build_system_prompt_for_chat()`, and `generate_tailored_cv()`. Extended Stage 2 prompt in `map_evidence()` to request differentiator categories and impact signals.
- **`core/validation.py`**: New `_check_generic_bullets()` soft-check function with generic-phrase regex, task-only detection, and missing-ownership-signal heuristics.
- **`core/models.py`**: Two new optional fields on `EvidenceMatch`: `differentiator_categories: list[str] = Field(default_factory=list)` and `impact_signals: list[str] = Field(default_factory=list)`.
- **`tests/test_pipeline.py`**: New tests for bullet strategy in prompts, differentiator fields in evidence map, Stage 2 prompt content.
- **`tests/test_validation.py`**: New `TestGenericBulletValidation` class.
- **`tests/test_models.py`**: New tests verifying optional field defaults.
- **No changes to**: providers (except prompt content), conftest fixtures (may add one generic-bullet fixture), backend, frontend, Docker, CI/CD.
