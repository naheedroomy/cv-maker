"""Cover letter generation, save, and PDF download endpoints."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.auth import get_current_user
from backend.db import get_db
from backend.schemas import CoverLetterRequest, CoverLetterResponse
from backend.tasks import schedule_background_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["cover-letter"])


# ---------------------------------------------------------------------------
# Background cover letter worker
# ---------------------------------------------------------------------------

async def _cover_letter_worker(
    job_id: str,
    user_id: int,
    model: str,
    user_notes: str,
    tone: str = "standard",
    writing_sample: str = "",
    model_id: str | None = None,
    reasoning_effort: str | None = None,
) -> None:
    """Run cover letter generation in the background, update DB on completion."""
    try:
        from core.cover_letter import generate_cover_letter
        from core.data import load_base_cv
        from core.models import GapItem, TailoredCV
        from core.providers import get_provider

        # Load job data
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT job_text, tailored_cv_json, gap_diff_json "
                "FROM jobs WHERE id=? AND user_id=?",
                (job_id, user_id),
            )
            row = await cursor.fetchone()
        finally:
            await db.close()

        if row is None:
            logger.error("Cover letter worker: job %s not found", job_id)
            return

        tailored_cv = TailoredCV.model_validate(json.loads(row["tailored_cv_json"]))
        gap_diff = [GapItem.model_validate(g) for g in json.loads(row["gap_diff_json"])]
        base_cv = await asyncio.to_thread(load_base_cv)
        provider = await get_provider(
            model,
            user_id=user_id,
            model_override=model_id,
            reasoning_effort=reasoning_effort,
        )

        cover_letter_text = await asyncio.to_thread(
            generate_cover_letter,
            provider,
            model,
            base_cv,
            row["job_text"],
            tailored_cv,
            gap_diff,
            user_notes,
            tone,
            writing_sample,
            reasoning_effort=reasoning_effort,
        )

        # Save result
        db = await get_db()
        try:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute(
                "UPDATE jobs SET cover_letter_text=?, cover_letter_notes=?, "
                "cover_letter_model=?, cover_letter_tone=? WHERE id=? AND user_id=?",
                (cover_letter_text, user_notes, model, tone, job_id, user_id),
            )
            await db.commit()
        finally:
            await db.close()

        # Lightweight audit — log AI-tell warnings internally
        try:
            from core.cover_letter_audit import audit_cover_letter
            audit = audit_cover_letter(cover_letter_text)
            if audit["warnings"]:
                logger.warning("Cover letter audit for job %s: word_count=%d, issues=%s",
                               job_id, audit["word_count"], audit["warnings"])
            else:
                logger.info("Cover letter audit for job %s: clean (word_count=%d)",
                            job_id, audit["word_count"])
        except Exception:
            logger.debug("Cover letter audit skipped (non-critical error)", exc_info=True)

        logger.info("Cover letter generated for job %s (tone=%s, model=%s)", job_id, tone, model)

    except Exception:
        # On failure, clear the generating marker so user can retry
        logger.exception("Cover letter generation failed for job %s", job_id)
        db = await get_db()
        try:
            await db.execute(
                "UPDATE jobs SET cover_letter_text=NULL WHERE id=? AND user_id=?",
                (job_id, user_id),
            )
            await db.commit()
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Endpoint 1: POST /{job_id}/cover-letter — generate cover letter (background)
# ---------------------------------------------------------------------------


@router.post("/{job_id}/cover-letter", status_code=202)
async def generate_cover_letter_endpoint(
    job_id: str,
    body: CoverLetterRequest,
    user: dict = Depends(get_current_user),
):
    """Start cover letter generation as a background task.

    Immediately clears old cover letter and returns 202. Frontend polls
    GET /api/jobs/{id} to detect completion (cover_letter_text goes from
    empty string to actual content).
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if row["status"] != "complete":
        raise HTTPException(
            status_code=409,
            detail="Job must be complete before generating cover letter",
        )
    if not row["tailored_cv_json"] or not row["gap_diff_json"]:
        raise HTTPException(status_code=409, detail="Job has no tailored CV data")

    # Archive existing cover letter into history (if it exists and is non-empty)
    cl_history: list[dict] = []
    if "cl_history_json" in row.keys() and row["cl_history_json"]:
        cl_history = json.loads(row["cl_history_json"])
    if row["cover_letter_text"] and len(row["cover_letter_text"]) > 0:
        version = len(cl_history) + 1
        cl_history.append({
            "version": version,
            "text": row["cover_letter_text"],
            "model": row["cover_letter_model"] if "cover_letter_model" in row.keys() else None,
            "tone": row["cover_letter_tone"] if "cover_letter_tone" in row.keys() else None,
            "created_at": row["updated_at"],
        })
    cl_history_json = json.dumps(cl_history) if cl_history else None

    # Clear old cover letter immediately — signals "generating" to frontend
    db = await get_db()
    try:
        await db.execute(
            "UPDATE jobs SET cover_letter_text='', cover_letter_notes=?, "
            "cover_letter_model=?, cover_letter_tone=?, cl_history_json=? "
            "WHERE id=? AND user_id=?",
            (body.user_notes, body.model, body.tone, cl_history_json, job_id, user["id"]),
        )
        await db.commit()
    finally:
        await db.close()

    # Fire and forget
    schedule_background_task(
        _cover_letter_worker(
            job_id,
            user["id"],
            body.model,
            body.user_notes,
            body.tone,
            body.writing_sample,
            model_id=body.model_id,
            reasoning_effort=body.reasoning_effort,
        )
    )

    return {"status": "generating"}


# ---------------------------------------------------------------------------
# Endpoint 2: PUT /{job_id}/cover-letter — save edited cover letter
# ---------------------------------------------------------------------------


class CoverLetterSaveRequest(BaseModel):
    cover_letter_text: str
    cover_letter_notes: str = ""


@router.put("/{job_id}/cover-letter", response_model=CoverLetterResponse)
async def save_cover_letter(
    job_id: str,
    body: CoverLetterSaveRequest,
    user: dict = Depends(get_current_user),
) -> CoverLetterResponse:
    """Save edited cover letter text back to the database."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")

        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE jobs SET cover_letter_text=?, cover_letter_notes=? WHERE id=? AND user_id=?",
            (body.cover_letter_text, body.cover_letter_notes, job_id, user["id"]),
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
async def get_cover_letter_pdf(job_id: str, user: dict = Depends(get_current_user)) -> Response:
    """Return cover letter as PDF bytes. 404 if no cover letter exists."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT cover_letter_text, tailored_cv_json FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
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

    from core.cover_letter_renderer import render_cover_letter_pdf

    pdf_bytes = await asyncio.to_thread(
        render_cover_letter_pdf, row["cover_letter_text"], candidate_name
    )
    return Response(content=pdf_bytes, media_type="application/pdf")
