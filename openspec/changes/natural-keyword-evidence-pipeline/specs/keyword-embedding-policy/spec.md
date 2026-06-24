## ADDED Requirements

### Requirement: Natural keyword limit per bullet

The system SHALL embed at most 2 distinct JD-derived keywords or key phrases in any single experience bullet. A "keyword" is defined as a specific technology, methodology, domain term, or responsibility phrase extracted from the JD requirements stage.

#### Scenario: Bullet with zero keywords is valid
- **WHEN** a bullet describes experience that is tangentially relevant but does not directly match any JD keyword
- **THEN** the system SHALL accept the bullet without requiring keyword injection

#### Scenario: Bullet with one keyword passes
- **WHEN** a bullet contains exactly 1 JD-derived keyword tied to a concrete action
- **THEN** the system SHALL consider it compliant

#### Scenario: Bullet with two keywords passes
- **WHEN** a bullet contains exactly 2 JD-derived keywords, both tied to actions or outcomes
- **THEN** the system SHALL consider it compliant

#### Scenario: Bullet with three or more keywords is flagged
- **WHEN** a bullet contains 3 or more distinct JD-derived keywords
- **THEN** the system SHALL emit a keyword-stuffing warning during validation

### Requirement: Keywords must be tied to concrete action or outcome

Every keyword embedded in an experience bullet SHALL be accompanied by a concrete action the candidate took or a measurable outcome achieved, not merely listed as a term the candidate "knows" or "has experience with."

#### Scenario: Keyword with action verb passes
- **WHEN** a bullet states "Built CI/CD pipelines with **GitHub Actions**" where the keyword is paired with an action verb
- **THEN** the system SHALL consider the keyword properly substantiated

#### Scenario: Keyword as bare mention is flagged
- **WHEN** a bullet states "Used Python, FastAPI, Docker, Kubernetes" without linking any keyword to a concrete action or outcome
- **THEN** the system SHALL emit a keyword-stuffing warning for unsubstantiated keywords

### Requirement: Related keyword pairing

When two keywords in the same bullet are semantically related (e.g., a technology and the methodology it enables, or two complementary tools in the same workflow), the system SHALL encourage but not require pairing them naturally within a single coherent statement rather than as an unconnected list.

#### Scenario: Natural pair in one bullet
- **WHEN** a bullet embeds "Kubernetes" and "auto-scaling" in the same sentence describing a coherent achievement
- **THEN** the system SHALL consider this compliant natural pairing

#### Scenario: Forced unrelated pair is flagged
- **WHEN** a bullet contains two unrelated keywords (e.g., "Python" and "Terraform") concatenated without a coherent narrative connection
- **THEN** the system SHALL emit a keyword cohesion warning

### Requirement: Keywords must be evidence-backed

Every keyword embedded in a tailored bullet SHALL map to at least one specific piece of evidence in the base CV (a bullet, technology list entry, skill, or project description) or an allowed inference rule (technology adjacency, responsibility adjacency, domain adjacency).

#### Scenario: Keyword with direct evidence passes
- **WHEN** the JD requires "PostgreSQL" and the base CV explicitly lists PostgreSQL in a role's technologies and bullets
- **THEN** the system SHALL accept the keyword as evidence-backed

#### Scenario: Keyword with inference evidence passes
- **WHEN** the JD requires "GCP" and the base CV shows deep AWS experience, allowing cloud-provider inference
- **THEN** the system SHALL accept the keyword if creativity level permits substitution and the inference is documented in tailoring notes

#### Scenario: Keyword without any evidence triggers warning
- **WHEN** the JD requires a technology not present in the base CV and no inference rule covers it
- **THEN** the system SHALL emit a keyword-without-evidence warning, unless the creativity level allows soft-fabrication with explicit tracking

### Requirement: Keywords SHALL NOT be dumped into skills section

The skills section SHALL ONLY contain technologies and capabilities demonstrably present in the base CV. The system SHALL NOT add JD-derived keywords to the skills section solely to inflate keyword match scores.

#### Scenario: Skills section limited to base CV evidence
- **WHEN** the tailored CV skills section is generated
- **THEN** every skill listed SHALL be traceable to the base CV skills, experience technologies, or an allowed inference rule at the current creativity level

#### Scenario: JD keyword dumped into skills triggers warning
- **WHEN** a JD keyword appears in skills but has no correlate in the base CV and no tailoring note documents its addition
- **THEN** the system SHALL emit a skills-keyword-dumping warning

### Requirement: Prompt-level policy applied across all provider paths

The natural keyword embedding policy SHALL be embedded in both `_build_prompt()` (Claude CLI single-shot path) and `_build_system_prompt_for_chat()` (chat-based provider path) as a dedicated rule section, resolved via `_resolve_rule()` with the existing creativity-level threshold mechanism.

#### Scenario: Keyword policy appears in Claude CLI prompt
- **WHEN** `_build_prompt()` is called at creativity level 2 with a keyword policy rule defined
- **THEN** the generated prompt SHALL contain the keyword embedding instructions

#### Scenario: Keyword policy appears in chat system prompt
- **WHEN** `_build_system_prompt_for_chat()` is called at creativity level 2
- **THEN** the generated system prompt SHALL contain the keyword embedding instructions

#### Scenario: Keyword policy respects creativity level
- **WHEN** `_build_prompt()` is called at creativity level 0 (STRICT)
- **THEN** the keyword policy SHALL still apply since keyword embedding is a formatting/discipline rule, not a content-generation rule
