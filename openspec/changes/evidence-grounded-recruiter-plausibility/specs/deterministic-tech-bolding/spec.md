## ADDED Requirements

### Requirement: Deterministic bolding function exists

The system SHALL provide a function `apply_tech_bolding(tailored: TailoredCV) -> TailoredCV` that post-processes a `TailoredCV` to apply `**bold**` markers to technology names in experience bullet text. The function SHALL mutate the `TailoredCV` in place and also return it.

#### Scenario: Bolding applied to bullet text
- **WHEN** a bullet contains "Managed Kubernetes clusters with Terraform" and the role's technologies include "Kubernetes" and "Terraform"
- **THEN** the function SHALL rewrite the bullet to "Managed **Kubernetes** clusters with **Terraform**"

#### Scenario: Already-bolded text is preserved
- **WHEN** a bullet already contains "**Kubernetes**" and the function encounters "Kubernetes" again
- **THEN** the function SHALL NOT double-bold (no `****Kubernetes****`)

### Requirement: Bolding uses highlighted_technologies and role technologies

The bolding function SHALL use two technology sources: the global `tailored.highlighted_technologies` list (bolded everywhere) and each role's `technologies` list (bolded only within that role's bullets). If a technology appears in both, it SHALL still be bolded once.

#### Scenario: Global highlighted tech bolded in all roles
- **WHEN** "Kubernetes" is in `highlighted_technologies`
- **THEN** "Kubernetes" SHALL be bolded in every role's bullets where it appears

#### Scenario: Role-specific tech bolded only in its role
- **WHEN** "FastAPI" is only in Role A's technologies, not in highlighted_technologies
- **THEN** "FastAPI" SHALL be bolded in Role A's bullets but NOT in Role B's bullets

### Requirement: Case-insensitive matching with word boundaries

The bolding function SHALL match technology names case-insensitively and with word boundaries, so that "Kubernetes" matches "kubernetes" but not "Kuberneteses". Multi-word technologies SHALL be matched as phrases (e.g., "GitHub Actions" SHALL match "github actions" as a contiguous phrase).

#### Scenario: Case-insensitive match
- **WHEN** a bullet contains "kubernetes" and the tech list has "Kubernetes"
- **THEN** the function SHALL bold it as "**kubernetes**" (preserving original case)

#### Scenario: Word boundary prevents partial match
- **WHEN** a bullet contains "Kuberneteses" and the tech list has "Kubernetes"
- **THEN** the function SHALL NOT bold the substring "Kubernetes" within "Kuberneteses"

### Requirement: Alias resolution for known abbreviations

The bolding function SHALL resolve known technology aliases before matching. Common abbreviations like "K8s" SHALL match "Kubernetes", "GH Actions" SHALL match "GitHub Actions". The alias map SHALL reuse the existing `_KEYWORD_ALIASES` constant from `core/validation.py` or define its own if that constant is validation-specific.

#### Scenario: Alias resolved for bolding
- **WHEN** a bullet contains "K8s" and the tech list has "Kubernetes"
- **THEN** the function SHALL bold "**K8s**"

### Requirement: Bolding preserves existing markdown and text structure

The bolding function SHALL preserve the original bullet text's structure, including existing bold markers, punctuation, and whitespace. Only the matched technology substring SHALL be wrapped in `**`.

#### Scenario: Original structure preserved
- **WHEN** a bullet is "Built CI/CD with GitHub Actions, reducing deploy time by 70%"
- **THEN** after bolding "GitHub Actions", the result SHALL be "Built CI/CD with **GitHub Actions**, reducing deploy time by 70%"

### Requirement: Bolding called after TailoredCV generation

The bolding function SHALL be called as a post-generation normalization step, after `TailoredCV.model_validate()` succeeds but before `validate_tailored_cv()` runs. This ensures validation sees the bolded output.

#### Scenario: Pipeline calls bolding post-generation
- **WHEN** `run_pipeline()` or `run_pipeline_staged()` completes generation
- **THEN** `apply_tech_bolding()` SHALL be called on the resulting `TailoredCV` before validation

### Requirement: Prompt clarifies core_competencies vs highlighted_technologies

The prompt SHALL be updated to explicitly distinguish `core_competencies` (capabilities and methodologies: GitOps, IaC, Observability, CI/CD, Cloud Infrastructure) from `highlighted_technologies` (concrete tools and platforms: Kubernetes, Terraform, AWS, Azure, Helm, ArgoCD, Datadog, Prometheus). This distinction SHALL appear in the existing `_RULES` for these concerns.

#### Scenario: Prompt clarifies the distinction
- **WHEN** the prompt references core_competencies or highlighted_technologies
- **THEN** it SHALL include language distinguishing capabilities from concrete tools
