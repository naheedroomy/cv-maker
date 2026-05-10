"""Job lifecycle API endpoints — POST, GET, DELETE, PDF, SSE."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterable
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from fastapi.responses import Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from backend.auth import get_current_user
from backend.db import get_db
from backend.schemas import JobCreate, JobResponse
from backend.tasks import schedule_background_task
from backend.worker import _job_tasks, _sse_queues, job_worker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

_TERMINAL_STATUSES = {"complete", "failed", "cancelled"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_response(row) -> JobResponse:
    """Convert an aiosqlite Row to a JobResponse model."""
    return JobResponse(
        id=row["id"],
        company_name=row["company_name"],
        job_link=row["job_link"],
        job_text=row["job_text"],
        model=row["model"],
        creativity_level=row["creativity_level"],
        applied=bool(row["applied"]),
        applied_at=row["applied_at"] if "applied_at" in row.keys() else None,
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        tailored_cv=json.loads(row["tailored_cv_json"]) if row["tailored_cv_json"] else None,
        gap_diff=json.loads(row["gap_diff_json"]) if row["gap_diff_json"] else None,
        pdf_url=f"/api/jobs/{row['id']}/pdf" if row["pdf_path"] else None,
        cover_letter_text=row["cover_letter_text"] if "cover_letter_text" in row.keys() else None,
        cover_letter_notes=row["cover_letter_notes"] if "cover_letter_notes" in row.keys() else None,
        cover_letter_model=row["cover_letter_model"] if "cover_letter_model" in row.keys() else None,
        cover_letter_tone=row["cover_letter_tone"] if "cover_letter_tone" in row.keys() else None,
        cv_history=json.loads(row["cv_history_json"]) if "cv_history_json" in row.keys() and row["cv_history_json"] else None,
        cl_history=json.loads(row["cl_history_json"]) if "cl_history_json" in row.keys() and row["cl_history_json"] else None,
    )


# ---------------------------------------------------------------------------
# Endpoint 1: POST / — create job (API-04)
# ---------------------------------------------------------------------------


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(body: JobCreate, user: dict = Depends(get_current_user)) -> JobResponse:
    """Submit a new CV tailoring job.

    Inserts a row with status='pending' and returns the job ID immediately.
    The pipeline runs in the background.
    """
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        # Check for duplicate job link (only when job_link is provided)
        if body.job_link:
            cursor = await db.execute(
                "SELECT id, company_name FROM jobs WHERE user_id=? AND job_link=?",
                (user["id"], body.job_link),
            )
            existing = await cursor.fetchone()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"A job with this link already exists: {existing['company_name']}",
                )

        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "INSERT INTO jobs "
            "(id, user_id, company_name, job_link, job_text, model, creativity_level, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (job_id, user["id"], body.company_name, body.job_link, body.job_text, body.model, body.creativity_level, now, now),
        )
        await db.commit()
    finally:
        await db.close()

    task = schedule_background_task(
        job_worker(job_id, body.company_name, body.job_text, body.model, body.creativity_level, user_id=user["id"])
    )
    _job_tasks[job_id] = task
    logger.info("Job %s created for company=%s model=%s creativity=%d", job_id, body.company_name, body.model, body.creativity_level)

    return JobResponse(
        id=job_id,
        company_name=body.company_name,
        model=body.model,
        creativity_level=body.creativity_level,
        status="pending",
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Endpoint 2: GET / — list all jobs (API-06)
# ---------------------------------------------------------------------------


@router.get("", response_model=list[JobResponse])
async def list_jobs(user: dict = Depends(get_current_user)) -> list[JobResponse]:
    """Return all jobs ordered by created_at descending."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC",
            (user["id"],),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [_row_to_response(row) for row in rows]


# ---------------------------------------------------------------------------
# Endpoint 3: GET /{job_id} — get job detail (API-05)
# ---------------------------------------------------------------------------


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, user: dict = Depends(get_current_user)) -> JobResponse:
    """Return a single job by ID. Returns 404 if not found."""
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

    return _row_to_response(row)


# ---------------------------------------------------------------------------
# Endpoint 4: DELETE /{job_id} — cancel job (API-07)
# ---------------------------------------------------------------------------


@router.delete("/{job_id}", status_code=204)
async def cancel_job(job_id: str, user: dict = Depends(get_current_user)) -> Response:
    """Cancel a pending or running job.

    Returns 204 on success, 404 if not found, 409 if already terminal.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT status FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if row["status"] in _TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail=f"Job already {row['status']}")

    task = _job_tasks.get(job_id)
    if task and not task.done():
        task.cancel()
        logger.info("Job %s cancellation requested", job_id)

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Endpoint 4b: DELETE /{job_id}/remove — permanently delete job
# ---------------------------------------------------------------------------


@router.delete("/{job_id}/remove", status_code=204)
async def delete_job(job_id: str, user: dict = Depends(get_current_user)) -> Response:
    """Permanently delete a job and its output files.

    Cancels the job if still running, then removes from database.
    Returns 204 on success, 404 if not found.
    """
    # Cancel if running
    task = _job_tasks.get(job_id)
    if task and not task.done():
        task.cancel()

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT pdf_path FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")

        # Delete output files if they exist
        if row["pdf_path"]:
            pdf_path = Path(row["pdf_path"])
            if pdf_path.exists():
                pdf_path.unlink()
            tex_path = pdf_path.with_suffix(".tex")
            if tex_path.exists():
                tex_path.unlink()

        await db.execute(
            "DELETE FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        await db.commit()
    finally:
        await db.close()

    _job_tasks.pop(job_id, None)
    logger.info("Job %s permanently deleted", job_id)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Endpoint 4c: PATCH /{job_id}/listing — update job link and text
# ---------------------------------------------------------------------------


class JobListingUpdate(BaseModel):
    job_link: str | None = None
    job_text: str | None = None


@router.patch("/{job_id}/listing", response_model=JobResponse)
async def update_job_listing(job_id: str, body: JobListingUpdate, user: dict = Depends(get_current_user)) -> JobResponse:
    """Update the job link and/or job listing text."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Job not found")

        updates = body.model_dump(exclude_none=True)
        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            values = list(updates.values()) + [job_id, user["id"]]
            await db.execute(f"UPDATE jobs SET {set_clause} WHERE id=? AND user_id=?", values)
            await db.commit()

        cursor = await db.execute("SELECT * FROM jobs WHERE id=? AND user_id=?", (job_id, user["id"]))
        row = await cursor.fetchone()
    finally:
        await db.close()

    return _row_to_response(row)


# ---------------------------------------------------------------------------
# Endpoint 4d: PATCH /{job_id}/applied — toggle applied status
# ---------------------------------------------------------------------------


@router.patch("/{job_id}/applied", response_model=JobResponse)
async def toggle_applied(job_id: str, user: dict = Depends(get_current_user)) -> JobResponse:
    """Toggle the applied status of a job."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT applied FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")

        new_val = 0 if row["applied"] else 1
        applied_at = None if new_val == 0 else datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE jobs SET applied=?, applied_at=? WHERE id=? AND user_id=?",
            (new_val, applied_at, job_id, user["id"]),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return _row_to_response(row)


# ---------------------------------------------------------------------------
# Endpoint 5: GET /{job_id}/pdf — download PDF (part of API-05)
# ---------------------------------------------------------------------------


@router.get("/{job_id}/pdf")
async def get_pdf(job_id: str, user: dict = Depends(get_current_user)) -> Response:
    """Return raw PDF bytes for a completed job.

    Returns 404 if not found or PDF not yet available.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT pdf_path, status FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if row["status"] != "complete" or row["pdf_path"] is None:
        raise HTTPException(status_code=404, detail="PDF not yet available")

    pdf_bytes = Path(row["pdf_path"]).read_bytes()
    return Response(content=pdf_bytes, media_type="application/pdf")


# ---------------------------------------------------------------------------
# Endpoint 5a: GET /{job_id}/pdf/{version} — download historical PDF
# ---------------------------------------------------------------------------


@router.get("/{job_id}/pdf/{version}")
async def get_pdf_version(job_id: str, version: int, user: dict = Depends(get_current_user)) -> Response:
    """Return PDF for a specific CV version from history."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT cv_history_json FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not row["cv_history_json"]:
        raise HTTPException(status_code=404, detail="No version history")

    history = json.loads(row["cv_history_json"])
    entry = next((h for h in history if h["version"] == version), None)
    if entry is None or not entry.get("pdf_path"):
        raise HTTPException(status_code=404, detail=f"Version {version} not found")

    pdf_path = Path(entry["pdf_path"])
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file no longer available")

    return Response(content=pdf_path.read_bytes(), media_type="application/pdf")


# ---------------------------------------------------------------------------
# Endpoint 5b: POST /{job_id}/regenerate — re-run CV pipeline on same job
# ---------------------------------------------------------------------------


class RegenerateRequest(BaseModel):
    model: str | None = None
    creativity_level: int | None = None


@router.post("/{job_id}/regenerate", response_model=JobResponse)
async def regenerate_job(job_id: str, body: RegenerateRequest, user: dict = Depends(get_current_user)) -> JobResponse:
    """Re-run CV tailoring on an existing job, preserving cover letter and metadata.

    Resets status to pending, clears CV output (tailored_cv, gap_diff, pdf),
    optionally updates model/creativity, and kicks off the worker.
    """
    # Cancel existing task if still running
    task = _job_tasks.get(job_id)
    if task and not task.done():
        task.cancel()

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE id=? AND user_id=?",
            (job_id, user["id"]),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")

        model = body.model or row["model"]
        creativity = body.creativity_level if body.creativity_level is not None else row["creativity_level"]
        now = datetime.now(timezone.utc).isoformat()

        # Archive current CV into history (if it exists)
        history: list[dict] = []
        if row["cv_history_json"]:
            history = json.loads(row["cv_history_json"])
        if row["tailored_cv_json"]:
            version = len(history) + 1
            history.append({
                "version": version,
                "model": row["model"],
                "creativity_level": row["creativity_level"],
                "pdf_path": row["pdf_path"],
                "created_at": row["updated_at"],
            })
        history_json = json.dumps(history) if history else None

        # Don't delete old PDF files — they're now referenced by history

        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            """UPDATE jobs SET
                status='pending', model=?, creativity_level=?,
                tailored_cv_json=NULL, gap_diff_json=NULL, pdf_path=NULL,
                cv_history_json=?,
                updated_at=?
            WHERE id=? AND user_id=?""",
            (model, creativity, history_json, now, job_id, user["id"]),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        updated_row = await cursor.fetchone()
    finally:
        await db.close()

    # Kick off worker
    new_task = schedule_background_task(
        job_worker(job_id, row["company_name"], row["job_text"], model, creativity, user_id=user["id"])
    )
    _job_tasks[job_id] = new_task
    logger.info("Job %s regenerating with model=%s creativity=%d", job_id, model, creativity)

    return _row_to_response(updated_row)


# ---------------------------------------------------------------------------
# Endpoint 6: GET /{job_id}/events — SSE stream (API-08)
# ---------------------------------------------------------------------------


@router.get("/{job_id}/events", response_class=EventSourceResponse)
async def job_events(job_id: str, user: dict = Depends(get_current_user)) -> AsyncIterable[ServerSentEvent]:
    """Stream real-time job status updates via Server-Sent Events.

    If the job is already terminal, yields one event and closes the stream.
    Otherwise subscribes to the worker's SSE queue until a terminal event arrives.
    """
    # Validate job existence
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

    # If job is already terminal, yield current state and close
    if row["status"] in _TERMINAL_STATUSES:
        yield ServerSentEvent(
            event="status",
            data=json.dumps(
                {
                    "id": job_id,
                    "status": row["status"],
                    "updated_at": row["updated_at"],
                }
            ),
        )
        return

    # Subscribe to events from the background worker
    q: asyncio.Queue = asyncio.Queue()
    _sse_queues.setdefault(job_id, set()).add(q)

    try:
        while True:
            try:
                item = await asyncio.wait_for(q.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # Keep-alive: continue waiting
                continue

            yield ServerSentEvent(
                event=item["event"],
                data=json.dumps(item["data"]),
            )

            # Stop streaming when terminal event received
            is_terminal = item["event"] == "complete" or item["data"].get(
                "status"
            ) in _TERMINAL_STATUSES
            if is_terminal:
                break
    finally:
        # Always remove queue to prevent memory leak on client disconnect
        _sse_queues.get(job_id, set()).discard(q)
