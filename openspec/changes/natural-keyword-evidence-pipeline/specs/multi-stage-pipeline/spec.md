## ADDED Requirements

### Requirement: Three-stage pipeline architecture

The system SHALL support a multi-stage CV tailoring pipeline composed of three sequential, independently invocable stages: Requirement Extraction, Evidence Mapping, and CV Generation. Each stage produces a typed intermediate artifact that feeds the next stage.

#### Scenario: Stages invoked sequentially
- **WHEN** `run_pipeline_staged()` is called with a BaseCV and JD text
- **THEN** Stage 1 (Requirement Extraction) runs first, then Stage 2 (Evidence Mapping) using Stage 1 output, then Stage 3 (CV Generation) using Stages 1 and 2 outputs

#### Scenario: Single-stage debugging
- **WHEN** only `extract_requirements()` is called
- **THEN** it SHALL produce a `RequirementExtraction` artifact without running subsequent stages

#### Scenario: Stage 3 receives only structured inputs
- **WHEN** Stage 3 (CV Generation) runs
- **THEN** it SHALL receive the evidence map and requirement extraction as structured Pydantic models, NOT the raw JD text

### Requirement: Requirement Extraction stage

Stage 1 SHALL parse a raw job description into a `RequirementExtraction` containing a list of `JDRequirement` items, each with: a keyword/phrase string, a category (technology, methodology, domain, responsibility, soft-skill), a priority tier (1-3), and a list of related phrases that are semantically linked to this requirement.

#### Scenario: Technology requirement extracted
- **WHEN** a JD states "Experience with Kubernetes and container orchestration"
- **THEN** Stage 1 SHALL produce a `JDRequirement` with phrase "Kubernetes", category "technology", tier based on JD emphasis, and related phrases including "container orchestration"

#### Scenario: Responsibility requirement extracted
- **WHEN** a JD states "You will design and implement CI/CD pipelines"
- **THEN** Stage 1 SHALL produce a `JDRequirement` with phrase "CI/CD pipelines", category "responsibility", and related phrases including "design", "implement"

#### Scenario: 8-12 keyword phrases extracted
- **WHEN** a JD of typical length (200-500 words) is processed
- **THEN** Stage 1 SHALL extract 8-12 distinct keyword phrases, avoiding both under-extraction (missing key requirements) and over-extraction (noise)

#### Scenario: Tier assignment reflects JD emphasis
- **WHEN** a JD mentions "must have strong Python experience" and "nice to have: Terraform"
- **THEN** "Python" SHALL be assigned tier 1 and "Terraform" assigned tier 3 (or 2 depending on context)

### Requirement: Evidence Mapping stage

Stage 2 SHALL map each `JDRequirement` from Stage 1 to concrete evidence in the base CV, producing an `EvidenceMap` containing `EvidenceMatch` items. Each match SHALL include: the requirement it maps to, a match_level (strong/partial/missing), the source location (company, role, bullet index or field name), and a list of allowed keywords that this evidence supports.

#### Scenario: Direct evidence match
- **WHEN** a JD requirement "PostgreSQL" has a matching technology and bullet in the base CV
- **THEN** Stage 2 SHALL produce an `EvidenceMatch` with match_level "strong", source pointing to the specific bullet, and allowed_keywords including "PostgreSQL"

#### Scenario: Partial evidence match via inference
- **WHEN** a JD requirement "GCP" has no direct base CV evidence but the candidate has AWS experience and creativity level permits cloud-provider inference
- **THEN** Stage 2 SHALL produce an `EvidenceMatch` with match_level "partial", source documenting the inference rule, and allowed_keywords including "GCP" with an inference flag

#### Scenario: Missing requirement
- **WHEN** a JD requirement "Rust" has no evidence in the base CV and no applicable inference rule
- **THEN** Stage 2 SHALL produce an `EvidenceMatch` with match_level "missing", empty source, and empty allowed_keywords

#### Scenario: Evidence map feeds keyword pairing plan
- **WHEN** Stage 2 completes
- **THEN** the `EvidenceMap` SHALL include a `KeywordPairingPlan` that groups keywords by their evidence source and suggests natural pairings (e.g., "Docker + Kubernetes" from the same role, "Python + FastAPI" from the same project)

### Requirement: CV Generation stage

Stage 3 SHALL generate a complete `TailoredCV` using ONLY the base CV data, the requirement extraction, the evidence map, and the keyword pairing plan. It SHALL NOT receive the raw JD text. The generation prompt SHALL instruct the model to write each experience bullet by consulting the evidence map to determine which keywords are substantiated, then embedding 1-2 allowed keywords naturally.

#### Scenario: Bullet written from evidence map
- **WHEN** Stage 3 writes a bullet for a role that has evidence for "PostgreSQL" and "query optimization"
- **THEN** the bullet SHALL embed at most 2 of the keywords from that role's evidence entries, tied to concrete actions

#### Scenario: No raw JD in Stage 3 prompt
- **WHEN** Stage 3 generates the prompt
- **THEN** the prompt SHALL contain the requirement extraction summary, evidence map, and keyword pairing plan, but SHALL NOT contain the raw JD text

#### Scenario: Stage 3 produces valid TailoredCV
- **WHEN** Stage 3 completes successfully
- **THEN** the output SHALL pass `TailoredCV.model_validate()` and SHALL pass all hard validation checks

### Requirement: Provider interface supports both single-shot and staged modes

The `BaseProvider` abstract class SHALL expose an optional `run_staged()` method that providers MAY implement for multi-stage mode. The existing `run()` method SHALL remain the primary interface for single-shot operation. Providers that do not implement `run_staged()` SHALL fall back to `run()`.

#### Scenario: Provider with staged support uses run_staged
- **WHEN** a provider implements `run_staged()` and the pipeline is invoked in staged mode
- **THEN** the system SHALL call `run_staged()` which internally manages the three prompts and artifact passing

#### Scenario: Provider without staged support falls back
- **WHEN** a provider does NOT implement `run_staged()` but the pipeline requests staged mode
- **THEN** the system SHALL fall back to the single-shot `run()` method with the existing combined prompt

#### Scenario: Single-shot run() interface unchanged
- **WHEN** `run()` is called on any provider
- **THEN** the signature, return type, and behavior SHALL be identical to the current implementation

### Requirement: Backward compatibility with existing single-shot pipeline

The existing `run_pipeline()` function in `core/pipeline.py` SHALL continue to work identically. The new staged pipeline functions SHALL be additive, not replacements. The keyword embedding policy SHALL be injected into both the single-prompt and multi-stage prompt builders.

#### Scenario: Existing run_pipeline tests pass unchanged
- **WHEN** the existing `test_pipeline.py` tests run against the modified code
- **THEN** all existing tests SHALL pass without modification

#### Scenario: run_pipeline still produces TailoredCV + gap_diff
- **WHEN** `run_pipeline(base_cv, job_text)` is called
- **THEN** it SHALL return `tuple[TailoredCV, list[GapItem]]` as before, with the keyword policy applied in the prompt

### Requirement: Prompt-level keyword policy in single-shot mode

Even in single-shot mode, the keyword embedding policy SHALL be included in the prompt as a dedicated rule section, resolved via the existing `_RULES` dict and `_resolve_rule()` mechanism at all creativity levels. This ensures consistent keyword discipline regardless of pipeline mode.

#### Scenario: Single-shot prompt includes keyword policy
- **WHEN** `_build_prompt()` is called at any creativity level
- **THEN** the generated prompt SHALL include the keyword embedding instructions from the resolved keyword rule

#### Scenario: Single-shot chat prompt includes keyword policy
- **WHEN** `_build_system_prompt_for_chat()` is called
- **THEN** the generated system prompt SHALL include the keyword embedding instructions
