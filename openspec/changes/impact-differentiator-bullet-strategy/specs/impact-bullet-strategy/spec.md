## ADDED Requirements

### Requirement: What + How + Result framing directive

The system SHALL include a prompt directive instructing the model to structure every experience bullet using the What + How + Result pattern: what was done (specific action/technology), how it was accomplished (method, scale, context), and what the result was (quantitative metric or qualitative impact). When numeric metrics are absent from the base CV, qualitative results such as "improved consistency," "standardized process," "reduced manual effort," or "enabled self-service" are acceptable if evidence-supported.

#### Scenario: Bullet with all three components passes review
- **WHEN** a bullet states "Designed reusable Terraform modules (What) for multi-environment provisioning across dev/staging/prod (How), eliminating per-environment copy-paste and reducing drift incidents by 80% (Result)"
- **THEN** the system SHALL consider it a well-formed impact bullet

#### Scenario: Task-only bullet is flagged by validation
- **WHEN** a bullet states "Managed Kubernetes deployments" with no specificity, context, or result
- **THEN** the validation system SHALL emit a generic-bullet warning

#### Scenario: Qualitative result is acceptable
- **WHEN** a bullet states "Built shared CI/CD templates adopted by 4 teams (What/How), standardizing deploy patterns across the org (qualitative Result)"
- **THEN** the validation system SHALL NOT flag it as lacking result, since "standardizing deploy patterns" is a qualitative impact

### Requirement: Depth-over-exposure signals

The prompt SHALL instruct the model to surface depth signals where the base CV supports them, including: reusable modules/libraries/templates created, standardization efforts, multi-environment experience (dev/staging/prod), scale context (number of services/teams/regions), and tool expertise beyond basic usage (custom operators, advanced configurations, migrations).

#### Scenario: Reusable module depth signal
- **WHEN** the base CV mentions shared Terraform modules
- **THEN** the prompt SHALL encourage phrasing like "Created reusable Terraform modules adopted by X teams" rather than "Used Terraform for infrastructure"

#### Scenario: No depth evidence — no fabricated depth
- **WHEN** the base CV does not substantiate reusable modules, standardization, or multi-environment work
- **THEN** the prompt SHALL NOT fabricate depth signals; the bullet SHALL still follow What + How + Result but at the appropriate depth level

### Requirement: Modern practice highlighting

The prompt SHALL instruct the model to highlight evidence-supported modern practices when present in the base CV, including: GitOps (Argo CD, Flux), platform engineering (Internal Developer Platforms, self-service), DevSecOps (shift-left security, policy as code), cost optimization (FinOps, right-sizing, reserved instances), observability beyond basic monitoring (metrics/logs/traces, SLOs, distributed tracing), and governance/compliance automation.

#### Scenario: GitOps practice highlighted
- **WHEN** the base CV mentions Argo CD or Flux
- **THEN** the prompt SHALL encourage surfacing GitOps as a practice label and describing the workflow concretely

#### Scenario: Modern practice not in evidence — not mentioned
- **WHEN** the base CV has no DevSecOps evidence
- **THEN** the prompt SHALL NOT fabricate DevSecOps claims

### Requirement: Ownership and leadership signals

The prompt SHALL instruct the model to surface ownership signals when base-CV evidence supports them: incident response / production ownership, cost optimization initiatives, security work (vulnerability scanning, secret management, policy validation, compliance), automation beyond CI/CD pipelines (Python/Shell operational automation), and for 4+ years experience, mentorship/leadership (mentoring, developer experience, reusable internal platforms, onboarding reduction).

#### Scenario: Incident response surfaced
- **WHEN** the base CV mentions on-call, incident response, or RCA
- **THEN** the prompt SHALL encourage bullets showing ownership: "Owned production incident response for X services, reducing MTTR by Y%"

#### Scenario: Mentorship for senior roles
- **WHEN** the base CV has 4+ years experience and mentions mentoring or team leadership
- **THEN** the prompt SHALL encourage surfacing mentorship impact: "Mentored X engineers, reducing onboarding time from Y to Z weeks"

### Requirement: Role-weighted bullet distribution

The prompt SHALL instruct the model to allocate bullets by role seniority: the current/latest role SHALL have 7-10 strong, detailed bullets with the highest differentiator density; previous roles SHALL have 5-7 simpler bullets appropriate to the era and stack of that role; older/less relevant roles SHALL have 2-3 bullets minimum.

#### Scenario: Current role gets most bullets
- **WHEN** the base CV has a current role with sufficient bullet material
- **THEN** the tailored CV SHALL allocate 7-10 bullets to that role and 5-7 to prior roles

#### Scenario: Role with sparse base CV keeps minimum
- **WHEN** a role in the base CV has only 3 bullets
- **THEN** the tailored CV SHALL keep all of them (minimum 2 constraint still applies) rather than fabricating additional bullets

### Requirement: Ideal bullet composition guidance

The prompt SHALL guide the model toward an ideal bullet composition across the CV: approximately 50% core skills bullets (demonstrating required technologies and methodologies), 30% advanced differentiator bullets (depth, modern practices, automation, cost/security), and 20% ownership/leadership bullets (incident response, mentorship, platform impact). This is aspirational guidance, not a hard constraint — deviations are acceptable when the base CV evidence does not support the ideal mix.

#### Scenario: Strong evidence supports the mix
- **WHEN** the base CV has strong evidence across core skills, differentiators, and ownership
- **THEN** the prompt SHALL encourage approximately the 50/30/20 distribution

#### Scenario: Junior base CV with limited differentiators
- **WHEN** the base CV has only core-skills evidence (no advanced differentiators or ownership)
- **THEN** the prompt SHALL NOT force-fabricate differentiator bullets; the distribution SHALL naturally skew toward core skills

### Requirement: Generic-bullet avoidance directive

The prompt SHALL explicitly instruct the model to avoid generic DevOps/cloud bullets that appear on most resumes, including "managed CI/CD pipelines," "deployed Kubernetes clusters," "provisioned infrastructure with Terraform," "set up monitoring with Prometheus/Grafana," and "collaborated with cross-functional teams." These are flagged as baseline tasks, not differentiators — the model SHALL rewrite them with specificity, context, scale, and result.

#### Scenario: Generic bullet rewritten with specificity
- **WHEN** the base CV says "Managed CI/CD pipelines with Jenkins"
- **THEN** the prompt SHALL guide rewriting to e.g. "Designed Jenkins shared-library pipeline framework adopted by X teams, cutting new-service CI/CD setup from 2 days to 2 hours"

#### Scenario: No extra evidence — minimum viable rewrite
- **WHEN** the base CV provides no additional context beyond "Managed CI/CD pipelines with Jenkins"
- **THEN** the prompt SHALL guide the model to add whatever specificity the base CV offers (company context, technology version, integration point) without fabrication

### Requirement: Prompt rule applied across all provider paths

The bullet strategy SHALL be embedded as a `"bullet_strategy"` rule in `_RULES` at level 0 and resolved in `_build_prompt()`, `_build_system_prompt_for_chat()`, and `generate_tailored_cv()` (Stage 3).

#### Scenario: Strategy appears in single-shot prompt
- **WHEN** `_build_prompt()` is called at any creativity level
- **THEN** the generated prompt SHALL contain the bullet strategy instructions

#### Scenario: Strategy appears in chat system prompt
- **WHEN** `_build_system_prompt_for_chat()` is called
- **THEN** the generated system prompt SHALL contain the bullet strategy instructions

#### Scenario: Strategy appears in Stage 3 staged prompt
- **WHEN** `generate_tailored_cv()` is called
- **THEN** the Stage 3 prompt SHALL contain the bullet strategy instructions
