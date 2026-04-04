"""Pydantic schemas for job API request/response contracts."""
from __future__ import annotations

from pydantic import BaseModel


class JobCreate(BaseModel):
    """Request body for POST /api/jobs."""

    company_name: str
    job_link: str | None = None
    job_text: str


class JobResponse(BaseModel):
    """Response model for all job endpoints."""

    id: str
    company_name: str
    status: str  # one of: pending, running, complete, failed, cancelled
    created_at: str  # ISO 8601 timestamp
    updated_at: str  # ISO 8601 timestamp
    tailored_cv: dict | None = None  # populated on complete (from tailored_cv_json column)
    gap_diff: list | None = None  # populated on complete (from gap_diff_json column)
    pdf_url: str | None = None  # populated on complete, format: /api/jobs/{id}/pdf


class CvConvertRequest(BaseModel):
    """Request body for POST /api/cv/convert."""

    cv_text: str  # Plain-text content of the CV to parse


class CvConvertResponse(BaseModel):
    """Response model for POST /api/cv/convert."""

    success: bool
    message: str
    contact_name: str | None = None  # Name parsed from the CV, for confirmation display
