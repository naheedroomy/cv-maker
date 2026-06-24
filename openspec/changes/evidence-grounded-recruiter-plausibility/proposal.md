## Why

The current pipeline produces CVs with strong keywords but some phrases feel mechanically shaped around the JD rather than reflecting real experience. Examples include a GitLab CI reference in a role where only GitHub Actions was used, awkward keyword chains like "Kubernetes container orchestration auto-scaling" instead of natural project language, and inconsistent technology highlighting across the PDF. These issues reduce recruiter plausibility — the CV reads as keyword-optimized rather than evidence-grounded. A recruiter scanning for real experience sees through mechanical JD mimicry. This change adds prompt-level plausibility rules, keyword-placement validation, optional evidence-placement fields on intermediate models, and deterministic technology bolding to produce CVs that match the JD through truthful, role-specific evidence.

## What Changes

- **Add recruiter plausibility prompt rule** as a new `"recruiter_plausibility"` entry in `_RULES` in `core/pipeline.py`, resolved at level 0. Covers: truthful evidence placement (keywords only in roles with real evidence), natural language over mechanical JD phrasing, preserving stronger base-CV bullets over generated rewrites, and distinguishing role-level bullet keywords from skills-only defensible keywords from omit-keywords.
- **Add optional `placement` and `placement_reason` fields** to `EvidenceMatch` in `core/models.py` (`placement`: `"experience"|"skills"|"omit"`, `placement_reason`: str). Backward compatible via `Field(default="experience")` and `Field(default="")`.
- **Extend Stage 2 Evidence Mapping prompt** to request placement guidance for each requirement, distinguishing where a keyword can be defensibly placed (experience bullet vs. skills section vs. omitted).
- **Add keyword-placement validation** in `core/validation.py`: soft warnings for suspicious role-keyword placement (keyword in wrong role), awkward keyword chains/noun stacks (3+ consecutive nouns/tech terms), JD mimicry phrases (copy-pasted JD language), over-dense bullets, highlighted technology not referenced in bullets, role technologies not in role bullets, and too many concrete tools in `core_competencies`.
- **Add deterministic technology bolding** function (new `core/bolding.py` or inline in `core/pipeline.py`/`core/validation.py`): post-generation normalization that applies `**bold**` markers to technology names in bullet text based on each role's `technologies` list and global `highlighted_technologies`, using case-insensitive matching, alias resolution, word boundaries, and existing-bold detection. Called after `TailoredCV` generation before validation.
- **Clarify prompt distinction** between `core_competencies` (capabilities/methodologies: GitOps, IaC, Observability) and `highlighted_technologies` (concrete tools/platforms: Kubernetes, Terraform, AWS).
- **Add tests/evals** for suspicious JD keywords (Jenkins, SonarQube, Nexus, IAM, OIDC, DNS, routing), role-specific evidence placement, awkward chain detection, deterministic bolding, and bolding consistency.
- **No breaking changes**: all new fields default to safe values. Existing prompt rules, models, provider interfaces unchanged. No UI/frontend/backend/DB changes. No new external dependencies.

## Capabilities

### New Capabilities

- `recruiter-plausibility-policy`: Prompt-level rules governing truthful keyword placement, natural language, bullet preservation, and evidence-grounded matching. Encodes rules against mechanical JD mimicry, wrong-role keywords, awkward chains, and skills-only defensible placement.
- `keyword-placement-validation`: Deterministic soft validation for suspicious role-keyword placement, awkward noun-stack chains, JD mimicry phrases, over-dense bullets, highlighted-tech reference consistency, role-technology consistency, and core-competencies tool leakage. Warnings only.
- `evidence-placement-fields`: Optional `placement` (`"experience"|"skills"|"omit"`) and `placement_reason` fields on `EvidenceMatch`, populated by Stage 2 evidence mapping to guide truthful keyword placement in Stage 3 generation.
- `deterministic-tech-bolding`: Post-generation normalization function that applies `**bold**` markers to technology names in bullet text based on `technologies` and `highlighted_technologies` lists, ensuring consistent PDF rendering independent of LLM output quality.

### Modified Capabilities

<!-- None — additive change building on prior pipeline capabilities. -->

## Impact

- **`core/pipeline.py`**: New `"recruiter_plausibility"` rule in `_RULES`, resolved and injected into all three prompt builders. Extended Stage 2 prompt with placement guidance. Add `apply_tech_bolding()` function (or new `core/bolding.py`).
- **`core/validation.py`**: New validation functions for placement, chain, mimicry, density, tech-reference, competencies-tool-leakage checks.
- **`core/models.py`**: `placement: str = Field(default="experience")` and `placement_reason: str = Field(default="")` on `EvidenceMatch`.
- **`tests/test_pipeline.py`**: New tests for plausibility rule in prompts, Stage 2 placement fields, bolding function.
- **`tests/test_validation.py`**: New `TestPlacementValidation` class.
- **`tests/conftest.py`**: Fixtures for suspicious JD keywords and role-specific evidence CVs.
- **No changes to**: providers, backend routes, frontend, Docker, CI/CD, LaTeX templates.
