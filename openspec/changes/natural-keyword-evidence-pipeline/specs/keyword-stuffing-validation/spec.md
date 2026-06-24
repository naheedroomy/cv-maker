## ADDED Requirements

### Requirement: Detect excessive keyword density in a single bullet

The system SHALL scan each tailored experience bullet for the count of distinct JD-derived keywords and emit a soft warning when a bullet contains 3 or more distinct keywords. "Distinct" means keywords that are not trivial variants of each other (case-insensitive, ignoring common suffixes like "ing", "ed", "s").

#### Scenario: Bullet with 0-2 keywords produces no warning
- **WHEN** a bullet contains 2 or fewer distinct JD keywords
- **THEN** the system SHALL NOT emit a keyword-stuffing warning for that bullet

#### Scenario: Bullet with 3 keywords triggers warning
- **WHEN** a bullet contains 3 or more distinct JD keywords (e.g., "Built **Kubernetes** clusters with **Terraform** and **Helm** for **CI/CD**")
- **THEN** the system SHALL emit a warning: "Keyword stuffing suspected: bullet contains N distinct JD keywords"

#### Scenario: Repeated keyword variants count as one
- **WHEN** a bullet contains "deploy", "deployment", and "deploying" — all variants of the same keyword root
- **THEN** the system SHALL count them as 1 distinct keyword, not 3

### Requirement: Detect keyword dumping in skills section

The system SHALL compare the tailored skills list against the evidence map (when available) or the base CV skills directly, and emit a warning when skills appear that have no documented evidence source.

#### Scenario: Skill with evidence produces no warning
- **WHEN** a skill like "Python" appears in both tailored skills and base CV skills
- **THEN** the system SHALL NOT emit a warning for that skill

#### Scenario: Unsubstantiated skill triggers warning
- **WHEN** a skill like "Terraform" appears in tailored skills but has no match in base CV skills, no experience bullet evidence, and no tailoring note documenting its addition
- **THEN** the system SHALL emit: "Unsubstantiated keyword in skills: 'Terraform' has no evidence trace in base CV"

### Requirement: Detect repeated keyword reuse across multiple bullets

The system SHALL detect when a keyword appears in too many bullets across the entire CV and emit a warning, as this suggests keyword stuffing rather than natural distribution. The threshold SHALL be configurable but default to 4 bullets per keyword.

#### Scenario: Keyword used in 1-3 bullets produces no warning
- **WHEN** a keyword appears in 3 or fewer bullets across the entire tailored CV
- **THEN** the system SHALL NOT emit a keyword reuse warning

#### Scenario: Keyword used in 4+ bullets triggers warning
- **WHEN** a keyword appears in 4 or more distinct bullets across the tailored CV
- **THEN** the system SHALL emit: "Keyword overused: 'Kubernetes' appears in N bullets — natural distribution is typically 1-3 mentions"

### Requirement: Detect bare keyword lists in bullets

The system SHALL detect bullets that consist primarily of a comma-separated list of technologies or keywords without substantive action or outcome language, and emit a warning.

#### Scenario: Bullet with action + keyword produces no warning
- **WHEN** a bullet pairs each keyword with a specific action (e.g., "Migrated **PostgreSQL** to **AWS RDS**, reducing costs by 30%")
- **THEN** the system SHALL NOT emit a bare-keyword-list warning

#### Scenario: Bullet that is only a keyword list triggers warning
- **WHEN** a bullet reads "Used Python, FastAPI, Docker, Kubernetes, Terraform, Helm" with no action or outcome
- **THEN** the system SHALL emit: "Keyword list detected: bullet appears to be a bare technology enumeration without substantive action"

### Requirement: All keyword-stuffing checks are soft warnings only

All keyword-stuffing validation checks SHALL emit soft warnings (returned in the warnings list) and SHALL NOT raise ValueError or block CV generation. This is intentional: keyword density can vary legitimately, and hard failures would break the pipeline for edge cases.

#### Scenario: Warnings do not block pipeline
- **WHEN** keyword-stuffing validation produces one or more warnings
- **THEN** `validate_tailored_cv()` SHALL return the warnings in its list and SHALL NOT raise any exception

#### Scenario: Clean CV returns only non-keyword warnings
- **WHEN** a tailored CV has no keyword-stuffing issues but has an invented metric
- **THEN** the returned warnings SHALL include the invented-metric warning but no keyword-stuffing warnings

### Requirement: Keyword matching uses normalized forms

The system SHALL normalize keywords before comparison: lowercase, strip punctuation, and match against a stemmed or root form so that "Kubernetes", "kubernetes", "K8s", and "k8s" are recognized as the same keyword (via an explicit alias map) while "Deployments" and "deploy" match via stemming.

#### Scenario: Case-insensitive matching
- **WHEN** the JD keyword is "Kubernetes" and a bullet contains "kubernetes"
- **THEN** the system SHALL count it as a match

#### Scenario: Stem-based matching
- **WHEN** the JD keyword is "deployment" and a bullet contains "deploying"
- **THEN** the system SHALL count it as a match via stemming

#### Scenario: Alias-based matching for known abbreviations
- **WHEN** the JD keyword is "Kubernetes" and a bullet contains "K8s"
- **THEN** the system SHALL count it as a match via the configured alias map
