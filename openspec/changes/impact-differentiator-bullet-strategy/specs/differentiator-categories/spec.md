## ADDED Requirements

### Requirement: EvidenceMatch gains optional differentiator_categories field

The `EvidenceMatch` model SHALL gain an optional `differentiator_categories` field of type `list[str]` with a default of an empty list. Valid category values include: "cost_optimization", "security", "mentorship", "platform_engineering", "incident_response", "automation", "observability", "governance", "developer_experience", "reliability", "scalability", "migration", "standardization". The field is populated by the evidence mapping stage when base-CV evidence supports a recruiter-valued differentiator.

#### Scenario: Field defaults to empty list
- **WHEN** an `EvidenceMatch` is created without specifying `differentiator_categories`
- **THEN** `differentiator_categories` SHALL be an empty list, not None

#### Scenario: Field populated by evidence mapping
- **WHEN** the base CV shows evidence of cost optimization (e.g., "reduced AWS spend by 30%")
- **THEN** the evidence mapping stage SHALL populate `differentiator_categories: ["cost_optimization"]` on the relevant match

#### Scenario: Serialization includes empty list
- **WHEN** `EvidenceMatch.model_dump()` is called on a match with default `differentiator_categories`
- **THEN** the output SHALL include `"differentiator_categories": []`

### Requirement: EvidenceMatch gains optional impact_signals field

The `EvidenceMatch` model SHALL gain an optional `impact_signals` field of type `list[str]` with a default of an empty list. Valid values include qualitative impact tags such as: "reduced_latency", "improved_consistency", "standardized_process", "automated_workflow", "reduced_manual_effort", "enabled_self_service", "improved_reliability", "reduced_onboarding_time", "increased_velocity", "reduced_cost", "improved_security_posture", "increased_coverage", "simplified_operations".

#### Scenario: Field defaults to empty list
- **WHEN** an `EvidenceMatch` is created without specifying `impact_signals`
- **THEN** `impact_signals` SHALL be an empty list, not None

#### Scenario: Qualitative impact tagged without numeric metric
- **WHEN** the base CV describes standardizing deploy patterns across teams but provides no numeric metric
- **THEN** the evidence mapping stage SHALL populate `impact_signals: ["standardized_process"]` on the relevant match

### Requirement: Stage 2 prompt requests differentiator categories and impact signals

The `map_evidence()` prompt in Stage 2 SHALL instruct the model to populate `differentiator_categories` and `impact_signals` for each `EvidenceMatch` where base-CV evidence supports them. The prompt SHALL include the valid category labels and instruct the model to leave the fields empty when no differentiator applies.

#### Scenario: Stage 2 prompt includes differentiator instructions
- **WHEN** `map_evidence()` builds its prompt
- **THEN** the prompt SHALL mention `differentiator_categories` and list valid values

#### Scenario: Stage 2 prompt includes impact signal instructions
- **WHEN** `map_evidence()` builds its prompt
- **THEN** the prompt SHALL mention `impact_signals` and instruct the model to tag qualitative impact

### Requirement: Fields use Field(default_factory=list) — no mutable defaults

Both `differentiator_categories` and `impact_signals` SHALL use `Field(default_factory=list)` to avoid shared mutable default values across model instances.

#### Scenario: Two EvidenceMatch instances have independent lists
- **WHEN** two `EvidenceMatch` instances are created with defaults
- **THEN** appending to one instance's `differentiator_categories` SHALL NOT affect the other

### Requirement: Existing EvidenceMatch callers are unaffected

All existing code that constructs `EvidenceMatch` without specifying `differentiator_categories` or `impact_signals` SHALL continue to work identically. The new fields are strictly additive.

#### Scenario: Existing test code works unchanged
- **WHEN** existing tests construct `EvidenceMatch(...)` without the new fields
- **THEN** the tests SHALL pass with `differentiator_categories=[]` and `impact_signals=[]` by default
