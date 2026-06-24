## ADDED Requirements

### Requirement: Detect suspicious role-keyword placement

The system SHALL detect when a JD keyword appears in the wrong role's bullets based on evidence-map placement guidance (when available). If no evidence map is available, the system SHALL check if a keyword in a role's bullet matches any technology in that role's `technologies` field — if not, and the keyword is a technology type, a soft warning SHALL be emitted.

#### Scenario: Keyword in correct role produces no warning
- **WHEN** "GitHub Actions" appears in a role whose base CV technologies include GitHub Actions
- **THEN** the system SHALL NOT emit a placement warning

#### Scenario: Keyword in wrong role triggers warning
- **WHEN** "GitLab CI" appears in a role whose base CV technologies do not include GitLab CI
- **THEN** the system SHALL emit a placement warning: "Suspicious placement: 'GitLab CI' may not be grounded in this role's evidence"

### Requirement: Detect awkward keyword chains and noun stacks

The system SHALL detect bullets containing 3+ consecutive capitalized nouns or technology terms without connecting verbs, articles, or prepositions, and emit a soft warning.

#### Scenario: Noun stack triggers warning
- **WHEN** a bullet reads "Kubernetes container orchestration auto-scaling"
- **THEN** the system SHALL emit: "Awkward keyword chain detected: 3+ consecutive nouns/tech terms — use natural project language"

#### Scenario: Natural sentence produces no warning
- **WHEN** a bullet reads "Designed auto-scaling for Kubernetes workloads using KEDA"
- **THEN** the system SHALL NOT emit a chain warning

### Requirement: Detect JD mimicry phrases

The system SHALL detect when bullet text contains phrases that appear to be copy-pasted or mechanically reshaped from the JD rather than written in natural candidate language. Heuristics include: bullet matches a JD requirement phrase near-verbatim (within 80% character similarity after stripping stopwords), or bullet uses the JD's exact phrasing for responsibilities ("design and implement," "build and maintain").

#### Scenario: JD-mimicry phrase triggers warning
- **WHEN** a bullet reads "Design and implement CI/CD pipelines" which matches the JD phrase "design and implement CI/CD pipelines"
- **THEN** the system SHALL emit: "Possible JD mimicry: bullet phrasing closely matches job description language"

#### Scenario: Natural rewrite produces no warning
- **WHEN** a bullet reads "Built CI/CD pipeline framework adopted by 4 teams, reducing deploy time by 70%"
- **THEN** the system SHALL NOT emit a mimicry warning

### Requirement: Detect highlighted technology not referenced in bullets

The system SHALL check that every entry in `highlighted_technologies` appears in at least one experience bullet or in the skills section. If a highlighted technology is never referenced in any bullet, a soft warning SHALL be emitted.

#### Scenario: Highlighted tech referenced in bullets — no warning
- **WHEN** "Kubernetes" is in highlighted_technologies and appears in at least one bullet
- **THEN** the system SHALL NOT emit a reference warning

#### Scenario: Orphan highlighted tech triggers warning
- **WHEN** "ArgoCD" is in highlighted_technologies but never appears in any bullet or skill
- **THEN** the system SHALL emit: "Highlighted technology 'ArgoCD' is never referenced in bullets — consider adding or removing"

### Requirement: Detect role technologies not in role bullets

The system SHALL check that each role's `technologies` field lists only tools that appear in that role's bullets (after stripping bold markers). If a technology is listed for a role but never mentioned in that role's bullets, a soft warning SHALL be emitted.

#### Scenario: Role tech in bullets — no warning
- **WHEN** a role lists "Python" in technologies and a bullet mentions Python
- **THEN** the system SHALL NOT emit a tech-reference warning

#### Scenario: Stale role tech triggers warning
- **WHEN** a role lists "Terraform" in technologies but no bullet in that role mentions Terraform
- **THEN** the system SHALL emit: "Role technology 'Terraform' not referenced in any bullet for this role"

### Requirement: Detect concrete tools in core_competencies

The system SHALL check that `core_competencies` contains capabilities/methodologies (GitOps, IaC, CI/CD, Observability) rather than concrete tool names. If `core_competencies` contains entries that match known tool names from `highlighted_technologies` or role `technologies`, a soft warning SHALL be emitted.

#### Scenario: Competency entry is a methodology — no warning
- **WHEN** `core_competencies` includes "Cloud Infrastructure" and "CI/CD"
- **THEN** the system SHALL NOT emit a tool-leakage warning

#### Scenario: Concrete tool in competencies triggers warning
- **WHEN** `core_competencies` includes "Kubernetes" which is a concrete tool
- **THEN** the system SHALL emit: "Concrete tool 'Kubernetes' in core_competencies — use highlighted_technologies for tools; core_competencies is for capabilities"

### Requirement: All placement validation checks are soft warnings

All keyword-placement validation checks SHALL emit soft warnings only and SHALL NOT raise ValueError or block CV generation.

#### Scenario: Warnings do not block pipeline
- **WHEN** placement validation produces warnings
- **THEN** `validate_tailored_cv()` SHALL return them in the warnings list without raising any exception
