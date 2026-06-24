## ADDED Requirements

### Requirement: JDRequirement model

The system SHALL define a `JDRequirement` Pydantic model with fields: `phrase` (str, the keyword or requirement phrase), `category` (Literal["technology", "methodology", "domain", "responsibility", "soft_skill"]), `tier` (int, 1-3), `related_phrases` (list[str], semantically linked terms), and `description` (str, the full sentence or clause from which this requirement was extracted).

#### Scenario: JDRequirement validates tier range
- **WHEN** a `JDRequirement` is created with tier=4
- **THEN** Pydantic validation SHALL raise a validation error

#### Scenario: JDRequirement validates category enum
- **WHEN** a `JDRequirement` is created with category="unknown"
- **THEN** Pydantic validation SHALL raise a validation error

#### Scenario: JDRequirement serializes to JSON
- **WHEN** `JDRequirement.model_dump()` is called
- **THEN** all fields SHALL be present in the output dict

### Requirement: EvidenceMatch model

The system SHALL define an `EvidenceMatch` Pydantic model with fields: `requirement_phrase` (str, the JD keyword this matches), `match_level` (Literal["strong", "partial", "missing"]), `source_company` (str | None), `source_role` (str | None), `source_bullet_index` (int | None, 0-based index into the role's bullets list), `source_field` (str | None, the base CV field name providing evidence), `evidence_text` (str, quoted or paraphrased evidence), `allowed_keywords` (list[str], JD keywords this evidence substantiates), and `inference_rule` (str | None, the inference rule name if match_level is "partial").

#### Scenario: Strong match has all source fields populated
- **WHEN** a `JDRequirement` "PostgreSQL" maps to a bullet in the base CV
- **THEN** the `EvidenceMatch` SHALL have match_level "strong", source_company, source_role, source_bullet_index, and evidence_text all populated

#### Scenario: Missing match has empty source fields
- **WHEN** a requirement has no base CV evidence
- **THEN** the `EvidenceMatch` SHALL have match_level "missing", source_company=None, source_role=None, source_bullet_index=None, evidence_text="", and allowed_keywords=[]

#### Scenario: Partial match references inference rule
- **WHEN** a requirement is matched via inference
- **THEN** the `EvidenceMatch` SHALL have match_level "partial" and inference_rule set to the rule name (e.g., "technology_adjacency")

### Requirement: KeywordPairingPlan model

The system SHALL define a `KeywordPairingPlan` Pydantic model with fields: `pairs` (list of `KeywordPair` items). Each `KeywordPair` SHALL have: `keywords` (list[str], 2-3 keywords that pair naturally), `rationale` (str, why these keywords go together), `evidence_source` (str, which base CV role/evidence substantiates this pair), and `suggested_bullet_count` (int, 1-2 bullets recommended for this pair).

#### Scenario: Keyword pair from same role
- **WHEN** "Docker" and "Kubernetes" are both substantiated by the same role in the base CV
- **THEN** a `KeywordPair` SHALL be created with both keywords and the rationale documenting the co-occurrence

#### Scenario: Keyword pair from different roles
- **WHEN** "Python" is substantiated by role A and "FastAPI" by role B
- **THEN** a `KeywordPair` MAY still be created if the pairing is natural, with the rationale noting the cross-role evidence

#### Scenario: Plan with no viable pairs
- **WHEN** no keywords naturally pair together
- **THEN** the `KeywordPairingPlan` SHALL have an empty pairs list — this is valid

### Requirement: RequirementExtraction model

The system SHALL define a `RequirementExtraction` Pydantic model with fields: `requirements` (list[JDRequirement]), `raw_jd_hash` (str, SHA-256 of the input JD text for traceability), and `model_metadata` (dict, provider/model info for debugging).

#### Scenario: Extraction wraps multiple requirements
- **WHEN** a JD is processed and 10 requirements are extracted
- **THEN** `RequirementExtraction.requirements` SHALL contain exactly 10 `JDRequirement` items

#### Scenario: Extraction includes JD hash
- **WHEN** `RequirementExtraction` is created
- **THEN** `raw_jd_hash` SHALL be the SHA-256 hex digest of the exact JD text that was processed

### Requirement: EvidenceMap model

The system SHALL define an `EvidenceMap` Pydantic model with fields: `matches` (list[EvidenceMatch], one per JD requirement), `pairing_plan` (KeywordPairingPlan), `coverage_summary` (dict with keys: total_requirements, strong_matches, partial_matches, missing), and `base_cv_hash` (str, SHA-256 of the serialized base CV for traceability).

#### Scenario: EvidenceMap coverage summary is correct
- **WHEN** 10 requirements are processed with 4 strong, 3 partial, and 3 missing matches
- **THEN** `coverage_summary` SHALL be {"total_requirements": 10, "strong_matches": 4, "partial_matches": 3, "missing": 3}

#### Scenario: EvidenceMap is serializable
- **WHEN** `EvidenceMap.model_dump()` is called
- **THEN** all nested models SHALL be serialized recursively

### Requirement: Models live in core/models.py

All new intermediate models SHALL be defined in `core/models.py` alongside the existing `BaseCV`, `TailoredCV`, `GapItem`, and `TailoringNote` models. They SHALL use Pydantic v2 (`BaseModel`, `field_validator`, `model_validator` from `pydantic`) consistent with the existing codebase style.

#### Scenario: Models imported from core.models
- **WHEN** any part of the pipeline imports models
- **THEN** `from core.models import JDRequirement, EvidenceMatch, ...` SHALL work without additional files

### Requirement: Existing models are not modified

The `BaseCV`, `TailoredCV`, `GapItem`, `TailoringNote`, and `JobRequirements` models SHALL remain unchanged. Their field definitions, validators, and serialization behavior SHALL be identical before and after this change.

#### Scenario: Existing model tests pass unchanged
- **WHEN** tests that construct and validate `BaseCV`, `TailoredCV`, `GapItem`, etc. run
- **THEN** all SHALL pass without modification to the test code
