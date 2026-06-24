## ADDED Requirements

### Requirement: Detect task-only bullets without specificity

The system SHALL scan each tailored experience bullet and emit a soft warning when a bullet describes only a task + technology with no additional specificity, context, scale, or result. A bullet is considered task-only if it matches the pattern: action verb + technology/tool name + optional prepositional phrase, with no numeric qualifier, scale indicator, team/org context, or outcome clause.

#### Scenario: Task-only bullet triggers warning
- **WHEN** a bullet reads "Managed Kubernetes deployments"
- **THEN** the system SHALL emit: "Generic bullet detected: task-only without specificity, context, or result — 'Managed Kubernetes deployments'"

#### Scenario: Specific bullet produces no warning
- **WHEN** a bullet reads "Managed 50+ Kubernetes clusters across 3 AWS regions, maintaining 99.95% uptime"
- **THEN** the system SHALL NOT emit a generic-bullet warning

### Requirement: Detect overused generic phrases

The system SHALL detect bullets that contain recruiter-flagged generic phrases and emit a warning. The blacklist SHALL include: "worked on", "responsible for", "helped with", "involved in", "collaborated with", "assisted with", "participated in", "supported", "handled", and "was part of". These phrases indicate passive participation rather than active ownership.

#### Scenario: Generic phrase triggers warning
- **WHEN** a bullet contains "worked on CI/CD pipelines"
- **THEN** the system SHALL emit: "Generic phrase detected: 'worked on' suggests passive participation — use active ownership language"

#### Scenario: Active verb produces no warning
- **WHEN** a bullet states "Built CI/CD pipelines with GitHub Actions"
- **THEN** the system SHALL NOT emit a generic-phrase warning for that bullet

### Requirement: Detect bullets lacking ownership/impact signal

The system SHALL check if the overall tailored CV has a reasonable proportion of bullets with ownership or impact signals. If fewer than 20% of bullets contain an ownership/impact keyword (incident, on-call, RCA, reduced, improved, automated, mentored, owned, led, designed, architected, saved, optimized, standardized, streamlined, eliminated, enabled, launched, migrated, scaled), a soft warning SHALL suggest improving ownership signal density.

#### Scenario: Sufficient ownership signals — no warning
- **WHEN** 30% of tailored bullets contain ownership/impact keywords
- **THEN** the system SHALL NOT emit an ownership-signal-density warning

#### Scenario: Low ownership signals — warning
- **WHEN** fewer than 20% of tailored bullets contain ownership/impact keywords
- **THEN** the system SHALL emit: "Low ownership signal: only X% of bullets contain impact/ownership language — consider surfacing results, mentorship, or ownership where base CV supports it"

### Requirement: Detect common generic DevOps bullet patterns

The system SHALL maintain a set of regex patterns for the most common generic DevOps bullets and emit a warning when an exact or near-match is found. Patterns include: "Managed/Deployed/Configured [tool] [preposition]", "Set up [tool] for [purpose]", "Used [tool] to [verb]". Near-match is defined as: the bullet text after stripping technology names and articles matches within 80% character similarity to a known generic pattern.

#### Scenario: Known generic pattern triggers warning
- **WHEN** a bullet reads "Set up monitoring with Prometheus and Grafana"
- **THEN** the system SHALL emit: "Common generic pattern detected: 'Set up monitoring with Prometheus and Grafana' — add specificity, scale, and result"

#### Scenario: Rewritten bullet avoids the pattern
- **WHEN** a bullet reads "Built Prometheus/Grafana observability stack with custom SLO dashboards, reducing incident detection time from 15min to 2min"
- **THEN** the system SHALL NOT emit a generic-pattern warning

### Requirement: All generic-bullet checks are soft warnings

All generic-bullet validation checks SHALL emit soft warnings only and SHALL NOT raise ValueError or block CV generation. Bullet quality assessment is inherently subjective — warnings guide review, not enforcement.

#### Scenario: Warnings do not block pipeline
- **WHEN** generic-bullet validation produces warnings
- **THEN** `validate_tailored_cv()` SHALL return them in the warnings list without raising any exception

#### Scenario: Generic warnings coexist with keyword and metric warnings
- **WHEN** a tailored CV has generic bullets AND keyword stuffing AND invented metrics
- **THEN** the warnings list SHALL contain all three categories of warnings

### Requirement: Generic-phrase check uses case-insensitive word-boundary matching

The system SHALL match generic phrases using case-insensitive, word-boundary regex so that "Worked on" matches "worked on" but not "networked on". The match SHALL also ignore the phrase when it appears in a negated or quoted context unlikely to indicate passive language (e.g., inside a proper noun or quoted tool name is acceptable to skip).

#### Scenario: Case-insensitive match
- **WHEN** a bullet starts with "WORKED ON infrastructure automation"
- **THEN** the system SHALL detect it as a generic phrase

#### Scenario: Word-boundary prevents false match
- **WHEN** a bullet contains "networked on-premise clusters"
- **THEN** the system SHALL NOT flag "worked on" because "networked" is not a match
