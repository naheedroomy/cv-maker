## ADDED Requirements

### Requirement: Truthful role-specific keyword placement rule

The prompt SHALL instruct the model to place JD keywords ONLY in experience roles where the base CV provides real, role-level evidence. If a keyword like "GitLab CI" has no evidence in the role being written, it SHALL NOT appear in that role's bullets. If the candidate used GitHub Actions in that role, the bullet SHALL say GitHub Actions, not GitLab CI.

#### Scenario: Keyword in wrong role is forbidden
- **WHEN** the base CV shows GitHub Actions used at Company A and GitLab CI used at Company B
- **THEN** the prompt SHALL instruct that Company A's bullets use GitHub Actions, not GitLab CI

#### Scenario: Keyword with no role-level evidence placed only in skills
- **WHEN** the base CV lists a technology in skills but no experience role substantiates it in a bullet
- **THEN** the prompt SHALL instruct that the keyword may appear in the skills section only if defensible, and SHALL NOT be forced into any experience bullet

### Requirement: Natural language over mechanical JD phrasing

The prompt SHALL instruct the model to use JD language inspiration but translate it into natural project descriptions. Avoid keyword chains like "Kubernetes container orchestration auto-scaling." Instead, write natural project sentences: "Designed an event-driven AWS pipeline using S3, SQS, and KEDA to autoscale Kubernetes workloads based on incoming demand."

#### Scenario: Keyword chain is discouraged
- **WHEN** a bullet contains 3+ consecutive nouns or technology terms without connecting language
- **THEN** the prompt SHALL discourage this pattern

#### Scenario: Natural project language is encouraged
- **WHEN** a bullet describes a real project with technologies woven into the narrative
- **THEN** the prompt SHALL consider this the preferred writing style

### Requirement: Preserve stronger base-CV bullets

The prompt SHALL instruct the model to keep base-CV bullets when they are already stronger or more accurate than what could be generated. If a base-CV bullet is well-written, specific, and truthful, it SHALL be preserved rather than rewritten. Generation is for improvement, not change for change's sake.

#### Scenario: Strong base-CV bullet is preserved
- **WHEN** the base CV has a bullet like "Built GitLab CI + CodeBuild hybrid pipeline for multi-cloud deployments" that is accurate and specific
- **THEN** the prompt SHALL instruct keeping it unchanged rather than rewriting it to match JD phrasing

### Requirement: Distinguish placement categories for keywords

The prompt SHALL instruct the model (in Stage 2 evidence mapping) to categorize each JD keyword by its defensible placement: "experience" (can be substantiated in a specific role's bullet), "skills" (defensible in skills section but not in bullets), or "omit" (no defensible placement — omit entirely).

#### Scenario: Skills-only keyword
- **WHEN** a JD keyword like "SonarQube" appears in the base CV skills list but no experience bullet substantiates actual usage
- **THEN** the evidence mapping SHALL categorize it as placement "skills"

#### Scenario: Omit keyword with no evidence
- **WHEN** a JD keyword has no evidence anywhere in the base CV
- **THEN** the evidence mapping SHALL categorize it as placement "omit"

### Requirement: 1-2 keywords per bullet, 3 only if naturally related

The prompt SHALL reinforce the keyword policy of 1-2 target keywords per experience bullet. Three keywords SHALL only appear when they are naturally related (e.g., part of the same project toolchain) and each has clear base-CV evidence.

#### Scenario: Three related keywords in one natural sentence
- **WHEN** a bullet describes "Built CI/CD pipelines with GitHub Actions, Docker, and Kubernetes for microservice deployments"
- **THEN** 3 keywords are acceptable because they form a coherent toolchain description

#### Scenario: Three unrelated keywords flagged
- **WHEN** a bullet contains "Used Jenkins, SonarQube, and IAM" with no connecting narrative
- **THEN** the system SHALL flag this as an awkward keyword chain

### Requirement: Prompt rule applied across all provider paths

The recruiter plausibility policy SHALL be embedded as a `"recruiter_plausibility"` rule in `_RULES` at level 0 and resolved in `_build_prompt()`, `_build_system_prompt_for_chat()`, and `generate_tailored_cv()` (Stage 3).

#### Scenario: Plausibility rule in all prompt builders
- **WHEN** any prompt builder is called
- **THEN** the generated prompt SHALL contain the recruiter plausibility instructions
