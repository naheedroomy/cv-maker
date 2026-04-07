"""Job lifecycle API endpoints — POST, GET, DELETE, PDF, SSE."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterable
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from backend.db import ANONYMOUS_USER_ID, get_db
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
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        tailored_cv=json.loads(row["tailored_cv_json"]) if row["tailored_cv_json"] else None,
        gap_diff=json.loads(row["gap_diff_json"]) if row["gap_diff_json"] else None,
        pdf_url=f"/api/jobs/{row['id']}/pdf" if row["pdf_path"] else None,
        cover_letter_text=row["cover_letter_text"] if "cover_letter_text" in row.keys() else None,
        cover_letter_notes=row["cover_letter_notes"] if "cover_letter_notes" in row.keys() else None,
    )


# ---------------------------------------------------------------------------
# Endpoint 1: POST / — create job (API-04)
# ---------------------------------------------------------------------------


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(body: JobCreate) -> JobResponse:
    """Submit a new CV tailoring job.

    Inserts a row with status='pending' and returns the job ID immediately.
    The pipeline runs in the background.
    """
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "INSERT INTO jobs "
            "(id, user_id, company_name, job_link, job_text, model, creativity_level, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (job_id, ANONYMOUS_USER_ID, body.company_name, body.job_link, body.job_text, body.model, body.creativity_level, now, now),
        )
        await db.commit()
    finally:
        await db.close()

    task = schedule_background_task(
        job_worker(job_id, body.company_name, body.job_text, body.model, body.creativity_level)
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
async def list_jobs() -> list[JobResponse]:
    """Return all jobs ordered by created_at descending."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC",
            (ANONYMOUS_USER_ID,),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [_row_to_response(row) for row in rows]


# ---------------------------------------------------------------------------
# Endpoint 3: GET /{job_id} — get job detail (API-05)
# ---------------------------------------------------------------------------


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Return a single job by ID. Returns 404 if not found."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE id=? AND user_id=?",
            (job_id, ANONYMOUS_USER_ID),
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
async def cancel_job(job_id: str) -> Response:
    """Cancel a pending or running job.

    Returns 204 on success, 404 if not found, 409 if already terminal.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT status FROM jobs WHERE id=? AND user_id=?",
            (job_id, ANONYMOUS_USER_ID),
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
async def delete_job(job_id: str) -> Response:
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
            (job_id, ANONYMOUS_USER_ID),
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
            (job_id, ANONYMOUS_USER_ID),
        )
        await db.commit()
    finally:
        await db.close()

    _job_tasks.pop(job_id, None)
    logger.info("Job %s permanently deleted", job_id)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Endpoint 4c: PATCH /{job_id}/applied — toggle applied status
# ---------------------------------------------------------------------------


@router.patch("/{job_id}/applied", response_model=JobResponse)
async def toggle_applied(job_id: str) -> JobResponse:
    """Toggle the applied status of a job."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT applied FROM jobs WHERE id=? AND user_id=?",
            (job_id, ANONYMOUS_USER_ID),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")

        new_val = 0 if row["applied"] else 1
        await db.execute(
            "UPDATE jobs SET applied=? WHERE id=? AND user_id=?",
            (new_val, job_id, ANONYMOUS_USER_ID),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM jobs WHERE id=? AND user_id=?",
            (job_id, ANONYMOUS_USER_ID),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return _row_to_response(row)


# ---------------------------------------------------------------------------
# Endpoint 5: GET /{job_id}/pdf — download PDF (part of API-05)
# ---------------------------------------------------------------------------


@router.get("/{job_id}/pdf")
async def get_pdf(job_id: str) -> Response:
    """Return raw PDF bytes for a completed job.

    Returns 404 if not found or PDF not yet available.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT pdf_path, status FROM jobs WHERE id=? AND user_id=?",
            (job_id, ANONYMOUS_USER_ID),
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
# Endpoint 6: GET /{job_id}/events — SSE stream (API-08)
# ---------------------------------------------------------------------------


@router.get("/{job_id}/events", response_class=EventSourceResponse)
async def job_events(job_id: str) -> AsyncIterable[ServerSentEvent]:
    """Stream real-time job status updates via Server-Sent Events.

    If the job is already terminal, yields one event and closes the stream.
    Otherwise subscribes to the worker's SSE queue until a terminal event arrives.
    """
    # Validate job existence
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE id=? AND user_id=?",
            (job_id, ANONYMOUS_USER_ID),
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
