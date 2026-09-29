# src/cv_maker/models.py
# All shared Pydantic v2 data models for the cv-maker pipeline.
# Every downstream component (renderer, AI layer, UI) imports from this module.
# Source: Pydantic v2 docs — https://docs.pydantic.dev/latest/concepts/models/
from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class ContactInfo(BaseModel):
    name: str
    email: str
    linkedin: str | None = None
    github: str | None = None
    phone: str | None = None
    location: str | None = None
    work_authorization: str | None = None  # e.g. "Possess a valid work permit in Germany (National Visa Type D)"


class LanguageItem(BaseModel):
    language: str  # e.g. "English"
    level: str  # e.g. "C2", "Native", "B1"


class ExperienceItem(BaseModel):
    company: str
    title: str
    location: str | None = None  # e.g. "Melbourne, Australia"
    # Stored as "YYYY-MM" strings — NOT Python date objects.
    # PyYAML silently converts bare 2021-03 to datetime.date; keep quoted in YAML.
    start: str
    end: str | None = None  # None = current role
    bullets: list[str]
    technologies: list[str] = []

    @field_validator("start", "end", mode="before")
    @classmethod
    def coerce_date_to_string(cls, v: object) -> str | None:
        """PyYAML converts bare YYYY-MM values to datetime.date; coerce back to string."""
        if v is None:
            return v
        import datetime

        if isinstance(v, (datetime.date, datetime.datetime)):
            return v.strftime("%Y-%m")
        return str(v)


class EducationItem(BaseModel):
    institution: str
    degree: str
    field: str | None = None
    year: int | None = None


class ProjectItem(BaseModel):
    name: str
    description: str
    technologies: list[str] = []
    url: str | None = None

    @field_validator("description", mode="before")
    @classmethod
    def coerce_none_to_empty_string(cls, v: object) -> str:
        """Replace null from JSON with empty string."""
        if v is None:
            return ""
        return str(v)


# ---------------------------------------------------------------------------
# Top-level pipeline models
# ---------------------------------------------------------------------------


class BaseCV(BaseModel):
    """The user's complete, unfiltered CV — all experience, all skills, all tools.

    This is the canonical source of truth loaded from base_cv.yaml.
    All AI tailoring operates on this model; nothing is fabricated.
    """

    contact: ContactInfo
    summary: str
    experience: list[ExperienceItem]
    skills: list[str]
    education: list[EducationItem]
    projects: list[ProjectItem] = []
    certifications: list[str] = []
    languages: list[LanguageItem] = []

    @field_validator("summary", mode="before")
    @classmethod
    def coerce_summary_none_to_empty(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v)


class JobRequirements(BaseModel):
    """The raw job listing as pasted by the user.

    DATA-02: No transformation applied at this layer — the string flows through
    the pipeline as-is. The AI layer (Phase 3) extracts structured requirements.
    """

    raw_text: str


class TailoredSection(BaseModel):
    """One rewritten CV section returned by Claude Code CLI."""

    section_name: str
    content: str | list[str]  # str for summary; list[str] for bullets


class GapItem(BaseModel):
    """One entry in the gap diff: a job requirement with match level and priority tier.

    DATA-03: Structured for UI display.
    - match_level="strong": base CV clearly demonstrates this requirement
    - match_level="partial": base CV has related/implicit evidence
    - match_level="missing": base CV does not demonstrate this requirement
    - tier: 1 (core tech stack), 2 (core responsibilities), 3 (nice-to-have)
    """

    requirement: str
    match_level: str  # "strong", "partial", or "missing"
    evidence: str  # Quote or reference from base CV; empty string when missing
    tier: int | None = None  # 1=must-have, 2=core, 3=nice-to-have; optional for backward compat


class TailoringNote(BaseModel):
    """One structured tailoring note — what was changed, why, and what it targets."""

    section: str  # Which CV section was changed (e.g., "Summary", "SyscoLabs experience")
    change: str  # What was changed
    reason: str  # Why it was changed — which job requirement it targets
    action: str  # "modified", "added", "removed", "reordered", or "unchanged"
    source: str = ""  # Evidence basis — base CV reference or inference rule; makes hallucination detectable


class TailoredCV(BaseModel):
    """Structured AI output — intermediate layer between Claude and LaTeX renderer.

    Defined in Phase 1 so all phases share a single import.
    Fields are designed conservatively: required fields are what Claude MUST return;
    all others default so TailoredCV.model_validate() is tolerant of minor Claude output variance.
    """

    contact: ContactInfo  # Pass-through from BaseCV
    summary: str
    experience: list[ExperienceItem]  # Rewritten by AI, reverse chronological
    skills: list[str]  # Filtered and reordered by AI
    education: list[EducationItem]  # Pass-through from BaseCV
    projects: list[ProjectItem] = []
    certifications: list[str] = []
    languages: list[LanguageItem] = []
    # AI-surfaced tools user knows but did not lead with in their base CV
    highlighted_technologies: list[str] = []
    # AI reasoning: structured notes on what was changed and why
    tailoring_notes: list[TailoringNote] = []
    # Gap diff: job requirements vs base CV evidence
    gap_diff: list[GapItem] = []
    # AI-selected keyword phrases from the JD that the candidate demonstrably matches
    core_competencies: list[str] = []

    # Regex to strip annotation labels that LLMs sometimes leak into bullet text
    _ANNOTATION_RE = re.compile(
        r"\s*\((?:substituted|soft[- ]?fabricated|added|removed|modified|reordered|unchanged)\)",
        re.IGNORECASE,
    )

    @field_validator("skills", mode="before")
    @classmethod
    def _normalize_skills(cls, v: object) -> list[str]:
        """Normalize skills from dicts or category objects into standard strings."""
        if not v:
            return []
        if isinstance(v, dict):
            return [
                f"{cat}: {', '.join(items) if isinstance(items, list) else items}"
                for cat, items in v.items()
                if cat and items
            ]
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, dict):
                    cat = item.get("category") or item.get("name") or ""
                    skills_list = item.get("skills") or item.get("items") or []
                    if cat:
                        if isinstance(skills_list, list):
                            items_str = ", ".join(
                                str(s).strip() for s in skills_list if str(s).strip()
                            )
                            res.append(f"{cat}: {items_str}")
                        else:
                            res.append(f"{cat}: {str(skills_list).strip()}")
                    elif skills_list:
                        if isinstance(skills_list, list):
                            res.extend(str(s).strip() for s in skills_list if str(s).strip())
                        else:
                            res.append(str(skills_list).strip())
                elif isinstance(item, str):
                    clean = item.strip()
                    if clean:
                        res.append(clean)
            return res
        return [str(v)]

    @field_validator("skills", mode="after")
    @classmethod
    def _cap_and_clean_skills(cls, v: list[str]) -> list[str]:
        """Deduplicate individual skills and enforce a 15-skill ceiling across categories."""
        total_skills = 0
        cleaned_categories: list[str] = []
        seen_skills: set[str] = set()

        for entry in v:
            if total_skills >= 15:
                break
            if ":" in entry:
                cat, rest = entry.split(":", 1)
                items = [s.strip() for s in rest.split(",") if s.strip()]
                kept_items: list[str] = []
                for item in items:
                    if total_skills >= 15:
                        break
                    if item.lower() not in seen_skills:
                        seen_skills.add(item.lower())
                        kept_items.append(item)
                        total_skills += 1
                if kept_items:
                    cleaned_categories.append(f"{cat.strip()}: {', '.join(kept_items)}")
            else:
                clean = entry.strip()
                if clean and clean.lower() not in seen_skills:
                    seen_skills.add(clean.lower())
                    cleaned_categories.append(clean)
                    total_skills += 1

        return cleaned_categories

    @model_validator(mode="after")
    def _strip_annotation_leaks(self) -> "TailoredCV":
        """Remove action labels like '(substituted)' from bullet text."""
        for exp in self.experience:
            exp.bullets = [self._ANNOTATION_RE.sub("", b) for b in exp.bullets]
        return self


# ---------------------------------------------------------------------------
# AI Pipeline models (Phase 3) — kept for backwards compatibility
# ---------------------------------------------------------------------------


class JobAnalysis(BaseModel):
    """Structured output from Claude step 1 (legacy — kept for test compatibility)."""

    role_title: str
    key_requirements: list[str]
    required_technologies: list[str]
    gap_diff: list[GapItem]


# ---------------------------------------------------------------------------
# Multi-stage pipeline intermediate models
# ---------------------------------------------------------------------------

# Valid categories for JD requirement classification
_JD_CATEGORIES = Literal["technology", "methodology", "domain", "responsibility", "soft_skill"]
# Valid match levels for evidence mapping
_MATCH_LEVELS = Literal["strong", "partial", "missing"]


class JDRequirement(BaseModel):
    """A single structured requirement extracted from a job description.

    Produced by Stage 1 (Requirement Extraction) of the multi-stage pipeline.
    """

    phrase: str  # The keyword or requirement phrase (e.g. "Kubernetes", "CI/CD pipelines")
    category: _JD_CATEGORIES = "technology"
    tier: int = 2  # 1=core tech stack, 2=core responsibilities, 3=nice-to-have
    related_phrases: list[str] = Field(default_factory=list)  # Semantically linked terms
    description: str = ""  # Full sentence/clause from which this requirement was extracted

    @field_validator("tier")
    @classmethod
    def _validate_tier(cls, v: int) -> int:
        if v not in (1, 2, 3):
            raise ValueError(f"tier must be 1, 2, or 3; got {v}")
        return v


class EvidenceMatch(BaseModel):
    """Maps a single JD requirement to concrete evidence in the base CV.

    Produced by Stage 2 (Evidence Mapping) of the multi-stage pipeline.
    """

    requirement_phrase: str  # The JD keyword this matches (from JDRequirement.phrase)
    match_level: _MATCH_LEVELS
    source_company: str | None = None
    source_role: str | None = None
    source_bullet_index: int | None = None  # 0-based index into the role's bullets list
    source_field: str | None = None  # Base CV field name providing evidence (e.g. "skills")
    evidence_text: str = ""  # Quoted or paraphrased evidence from base CV
    allowed_keywords: list[str] = Field(default_factory=list)  # JD keywords this evidence substantiates
    inference_rule: str | None = None  # Inference rule name if match_level is "partial"
    # Recruiter-valued differentiator categories this evidence supports.
    # Valid values: cost_optimization, security, mentorship, platform_engineering,
    #   incident_response, automation, observability, governance, developer_experience,
    #   reliability, scalability, migration, standardization.
    differentiator_categories: list[str] = Field(default_factory=list)
    # Qualitative impact tags for evidence that shows impact without numeric metrics.
    # Valid values: reduced_latency, improved_consistency, standardized_process,
    #   automated_workflow, reduced_manual_effort, enabled_self_service,
    #   improved_reliability, reduced_onboarding_time, increased_velocity,
    #   reduced_cost, improved_security_posture, increased_coverage, simplified_operations.
    impact_signals: list[str] = Field(default_factory=list)
    # Keyword placement guidance: where this keyword can be defensibly placed.
    # "experience" = can embed in an experience bullet, "skills" = skills section
    # only, "omit" = no defensible placement — omit entirely.
    placement: str = "experience"
    # Reason for the placement decision (e.g., "Only in base CV skills, no bullet evidence").
    placement_reason: str = ""


class KeywordPair(BaseModel):
    """A natural pairing of 2-3 keywords that belong together in a bullet.

    Part of the KeywordPairingPlan produced during evidence mapping.
    """

    keywords: list[str]  # 2-3 keywords that pair naturally
    rationale: str = ""  # Why these keywords go together
    evidence_source: str = ""  # Which base CV role/evidence substantiates this pair
    suggested_bullet_count: int = 1  # 1-2 bullets recommended for this pair


class KeywordPairingPlan(BaseModel):
    """Plan for embedding keywords in experience bullets as natural pairs.

    Produced during Stage 2 (Evidence Mapping) to guide Stage 3 (CV Generation).
    """

    pairs: list[KeywordPair] = Field(default_factory=list)


class RequirementExtraction(BaseModel):
    """Complete output of Stage 1: structured requirements extracted from a JD.

    Contains the full list of JDRequirement items plus traceability metadata.
    """

    requirements: list[JDRequirement]
    raw_jd_hash: str = ""  # SHA-256 of the input JD text for traceability
    model_metadata: dict = Field(default_factory=dict)  # Provider/model info for debugging


class EvidenceMap(BaseModel):
    """Complete output of Stage 2: evidence mapping for all JD requirements.

    Maps every requirement to base-CV evidence (or marks it missing), and
    provides a keyword pairing plan to guide natural keyword embedding in Stage 3.
    """

    matches: list[EvidenceMatch]  # One match per JD requirement
    pairing_plan: KeywordPairingPlan = Field(default_factory=KeywordPairingPlan)
    coverage_summary: dict = Field(default_factory=dict)  # e.g. {"total_requirements": 10, ...}
    base_cv_hash: str = ""  # SHA-256 of the serialized base CV for traceability
