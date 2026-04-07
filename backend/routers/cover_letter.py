"""Cover letter generation, save, and PDF download endpoints."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.db import get_db
from backend.schemas import CoverLetterRequest, CoverLetterResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["cover-letter"])


# ---------------------------------------------------------------------------
# Endpoint 1: POST /{job_id}/cover-letter — generate cover letter (D-07)
# ---------------------------------------------------------------------------


@router.post("/{job_id}/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter_endpoint(job_id: str, body: CoverLetterRequest) -> CoverLetterResponse:
    """Generate a cover letter for a completed job.

    Requires job status == 'complete' with tailored_cv_json and gap_diff_json populated.
    Runs inline (not background) — cover letter generation is fast (~5-15s).
    """
    # 1. Fetch job, verify complete status
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if row["status"] != "complete":
        raise HTTPException(status_code=409, detail="Job must be complete before generating cover letter")
    if not row["tailored_cv_json"] or not row["gap_diff_json"]:
        raise HTTPException(status_code=409, detail="Job has no tailored CV data")

    # 2. Parse stored data
    from cv_maker.models import GapItem, TailoredCV
    from cv_maker.data import load_base_cv

    tailored_cv = TailoredCV.model_validate(json.loads(row["tailored_cv_json"]))
    gap_diff = [GapItem.model_validate(g) for g in json.loads(row["gap_diff_json"])]

    # 3. Load base CV (sync I/O via thread pool)
    base_cv = await asyncio.to_thread(load_base_cv)

    # 4. Generate cover letter (sync LLM call via thread pool)
    from cv_maker.cover_letter import generate_cover_letter

    cover_letter_text = await asyncio.to_thread(
        generate_cover_letter,
        body.model,
        base_cv,
        row["job_text"],
        tailored_cv,
        gap_diff,
        body.user_notes,
        body.tone,
    )

    # 5. Store in DB
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE jobs SET cover_letter_text=?, cover_letter_notes=? WHERE id=?",
            (cover_letter_text, body.user_notes, job_id),
        )
        await db.commit()
    finally:
        await db.close()

    logger.info("Cover letter generated for job %s (tone=%s, model=%s)", job_id, body.tone, body.model)
    return CoverLetterResponse(
        cover_letter_text=cover_letter_text,
        cover_letter_notes=body.user_notes,
    )


# ---------------------------------------------------------------------------
# Endpoint 2: PUT /{job_id}/cover-letter — save edited cover letter
# ---------------------------------------------------------------------------


class CoverLetterSaveRequest(BaseModel):
    cover_letter_text: str
    cover_letter_notes: str = ""


@router.put("/{job_id}/cover-letter", response_model=CoverLetterResponse)
async def save_cover_letter(job_id: str, body: CoverLetterSaveRequest) -> CoverLetterResponse:
    """Save edited cover letter text back to the database."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM jobs WHERE id=?", (job_id,))
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")

        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE jobs SET cover_letter_text=?, cover_letter_notes=? WHERE id=?",
            (body.cover_letter_text, body.cover_letter_notes, job_id),
        )
        await db.commit()
    finally:
        await db.close()

    return CoverLetterResponse(
        cover_letter_text=body.cover_letter_text,
        cover_letter_notes=body.cover_letter_notes,
    )


# ---------------------------------------------------------------------------
# Endpoint 3: GET /{job_id}/cover-letter/pdf — download cover letter as PDF
# ---------------------------------------------------------------------------


@router.get("/{job_id}/cover-letter/pdf")
async def get_cover_letter_pdf(job_id: str) -> Response:
    """Return cover letter as PDF bytes. 404 if no cover letter exists."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT cover_letter_text, tailored_cv_json FROM jobs WHERE id=?", (job_id,)
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not row["cover_letter_text"]:
        raise HTTPException(status_code=404, detail="No cover letter generated yet")

    # Extract candidate name from tailored CV for PDF header
    candidate_name = ""
    if row["tailored_cv_json"]:
        try:
            cv_data = json.loads(row["tailored_cv_json"])
            candidate_name = cv_data.get("contact", {}).get("name", "")
        except (json.JSONDecodeError, KeyError):
            pass

    from cv_maker.cover_letter_renderer import render_cover_letter_pdf

    pdf_bytes = await asyncio.to_thread(
        render_cover_letter_pdf, row["cover_letter_text"], candidate_name
    )
    return Response(content=pdf_bytes, media_type="application/pdf")
