## ADDED Requirements

### Requirement: EvidenceMatch gains optional placement field

The `EvidenceMatch` model SHALL gain an optional `placement` field of type `str` with a default value of `"experience"`. Valid values: `"experience"` (can be embedded in an experience bullet), `"skills"` (defensible in skills section only, not in bullets), `"omit"` (no defensible placement — omit entirely). The field SHALL use `Field(default="experience")` — a string immutable default is safe.

#### Scenario: Field defaults to "experience"
- **WHEN** an `EvidenceMatch` is created without specifying `placement`
- **THEN** `placement` SHALL be `"experience"`

#### Scenario: Skills-only placement
- **WHEN** the evidence mapping determines a keyword can only appear in skills
- **THEN** the match SHALL have `placement: "skills"`

#### Scenario: Omit placement
- **WHEN** the evidence mapping determines a keyword has no defensible placement
- **THEN** the match SHALL have `placement: "omit"`

### Requirement: EvidenceMatch gains optional placement_reason field

The `EvidenceMatch` model SHALL gain an optional `placement_reason` field of type `str` with a default value of `""`. This documents why a particular placement was chosen (e.g., "Only listed in base CV skills, no bullet evidence").

#### Scenario: Field defaults to empty string
- **WHEN** an `EvidenceMatch` is created without specifying `placement_reason`
- **THEN** `placement_reason` SHALL be `""`

#### Scenario: Reason populated by evidence mapping
- **WHEN** the evidence mapping places a keyword in "skills"
- **THEN** the match SHALL have a non-empty `placement_reason` explaining the decision

### Requirement: Stage 2 prompt requests placement fields

The `map_evidence()` prompt in Stage 2 SHALL instruct the model to populate `placement` and `placement_reason` for each `EvidenceMatch`. The prompt SHALL explain the three placement categories and instruct the model to choose based on evidence strength.

#### Scenario: Stage 2 prompt includes placement instructions
- **WHEN** `map_evidence()` builds its prompt
- **THEN** the prompt SHALL mention `placement` field with values "experience", "skills", "omit"

### Requirement: Existing EvidenceMatch callers are unaffected

All existing code that constructs `EvidenceMatch` without specifying `placement` or `placement_reason` SHALL continue to work identically. The new fields default to `"experience"` and `""`, which preserves existing semantics (keywords default to experience placement).

#### Scenario: Existing test code works unchanged
- **WHEN** existing tests construct `EvidenceMatch(...)` without the new fields
- **THEN** the tests SHALL pass with `placement="experience"` and `placement_reason=""` by default
