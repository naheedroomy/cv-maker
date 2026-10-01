"""Pydantic schemas for job API request/response contracts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    """Request body for POST /api/jobs."""

    company_name: str
    job_link: str | None = None
    job_text: str
    model: str = "claude-haiku"
    model_id: str | None = None
    reasoning_effort: str | None = None
    creativity_level: int = Field(default=2, ge=0, le=3)
    user_notes: str = ""
    base_cv_id: str | None = None


class JobResponse(BaseModel):
    """Response model for all job endpoints."""

    id: str
    company_name: str
    job_link: str | None = None
    job_text: str | None = None
    model: str = "claude-haiku"
    model_id: str | None = None
    reasoning_effort: str | None = None
    creativity_level: int = 2
    applied: bool = False
    applied_at: str | None = None  # ISO 8601 timestamp when applied was toggled to true
    status: str  # one of: pending, running, complete, failed, cancelled
    created_at: str  # ISO 8601 timestamp
    updated_at: str  # ISO 8601 timestamp
    tailored_cv: dict | None = None  # populated on complete (from tailored_cv_json column)
    gap_diff: list | None = None  # populated on complete (from gap_diff_json column)
    pdf_url: str | None = None  # populated on complete, format: /api/jobs/{id}/pdf
    cover_letter_text: str | None = None  # populated when cover letter is generated
    cover_letter_notes: str | None = None  # user notes used for generation
    cover_letter_model: str | None = None  # model used for cover letter generation
    cover_letter_tone: str | None = None  # tone used for cover letter generation
    cv_history: list[dict] | None = None  # previous CV versions
    cl_history: list[dict] | None = None  # previous cover letter versions
    user_notes: str | None = None  # user guidance notes for tailoring
    base_cv_id: str | None = None
    base_cv_name: str | None = None


class CvConvertRequest(BaseModel):
    """Request body for POST /api/cv/convert."""

    cv_text: str  # Plain-text content of the CV to parse
    model: str = "claude-haiku"  # Provider to use for parsing


class CvConvertResponse(BaseModel):
    """Response model for POST /api/cv/convert."""

    success: bool
    message: str
    contact_name: str | None = None  # Name parsed from the CV, for confirmation display
    yaml_content: str | None = None  # The generated YAML content for preview


class CoverLetterRequest(BaseModel):
    """Request body for POST /api/jobs/:id/cover-letter."""

    model: str = "claude-haiku"
    model_id: str | None = None
    reasoning_effort: str | None = None
    tone: str = Field(
        default="standard",
        description="Cover letter voice style. Defaults to standard.",
    )
    user_notes: str = ""
    writing_sample: str = ""


class CoverLetterResponse(BaseModel):
    """Response model for cover letter generation."""

    cover_letter_text: str
    cover_letter_notes: str = ""


class CvUploadResponse(BaseModel):
    """Response for POST /api/cv/upload."""

    success: bool
    message: str
    cv: dict | None = None  # Parsed BaseCV as dict
    base_cv_id: str | None = None
    name: str | None = None


class BaseCvMeta(BaseModel):
    """Summary metadata for a user's Base CV."""

    id: str
    name: str
    is_default: bool
    created_at: str
    updated_at: str


class BaseCvDetail(BaseModel):
    """Full detail of a user's Base CV including parsed CV JSON."""

    id: str
    name: str
    is_default: bool
    created_at: str
    updated_at: str
    cv: dict


class BaseCvCreate(BaseModel):
    """Request model for creating a new Base CV."""

    name: str
    cv: dict | None = None
    source_id: str | None = None
    is_default: bool = False


class BaseCvUpdate(BaseModel):
    """Request model for updating an existing Base CV."""

    name: str | None = None
    cv: dict | None = None
    is_default: bool | None = None


class CvMeResponse(BaseModel):
    """Response for GET /api/cv/me."""

    has_cv: bool
    cv: dict | None = None  # BaseCV as dict, None if no CV saved

