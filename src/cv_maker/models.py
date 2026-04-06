# src/cv_maker/models.py
# All shared Pydantic v2 data models for the cv-maker pipeline.
# Every downstream component (renderer, AI layer, UI) imports from this module.
# Source: Pydantic v2 docs — https://docs.pydantic.dev/latest/concepts/models/
from __future__ import annotations

from pydantic import BaseModel, field_validator

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


class ExperienceItem(BaseModel):
    company: str
    title: str
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
    # AI-surfaced tools user knows but did not lead with in their base CV
    highlighted_technologies: list[str] = []
    # AI reasoning: structured notes on what was changed and why
    tailoring_notes: list[TailoringNote] = []
    # Gap diff: job requirements vs base CV evidence
    gap_diff: list[GapItem] = []


# ---------------------------------------------------------------------------
# AI Pipeline models (Phase 3) — kept for backwards compatibility
# ---------------------------------------------------------------------------


class JobAnalysis(BaseModel):
    """Structured output from Claude step 1 (legacy — kept for test compatibility)."""

    role_title: str
    key_requirements: list[str]
    required_technologies: list[str]
    gap_diff: list[GapItem]
