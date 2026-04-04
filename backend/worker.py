"""Background job worker with semaphore, task registry, and SSE event queues.

The worker coroutine drives the entire CV generation pipeline:
  pending -> running -> complete (or failed / cancelled)

Concurrency is limited to 2 simultaneous pipeline runs via asyncio.Semaphore(2).
SSE subscribers register queues in _sse_queues; the worker pushes events at each
status transition. CancelledError is caught, DB updated, then re-raised.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.db import get_db
from backend.pipeline_runner import render_pdf_async, run_pipeline_async
from cv_maker.data import load_base_cv
from cv_maker.renderer import render_latex

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

# Semaphore: at most 2 concurrent pipeline runs (Claude CLI is CPU/IO-heavy)
_semaphore = asyncio.Semaphore(2)

# Job ID -> asyncio.Task; populated by the router on submit, used for cancellation
_job_tasks: dict[str, asyncio.Task] = {}

# Job ID -> set of asyncio.Queue; SSE generators register to receive events
_sse_queues: dict[str, set[asyncio.Queue]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


async def _push_event(job_id: str, event_type: str, data: dict) -> None:
    """Push an SSE event to all queues watching this job."""
    for q in _sse_queues.get(job_id, set()):
        await q.put({"event": event_type, "data": data})


# ---------------------------------------------------------------------------
# Main worker coroutine
# ---------------------------------------------------------------------------


async def job_worker(job_id: str, company_name: str, job_text: str) -> None:
    """Background worker: runs pipeline, saves PDF, updates DB at each stage.

    Status transitions:
      pending -> running (on semaphore acquire)
      running -> complete (on success)
      running -> cancelled (on CancelledError)
      running/pending -> failed (on any other exception)

    Catches ALL exceptions including CancelledError.
    On CancelledError: sets status='cancelled', re-raises (MUST re-raise per asyncio contract).
    On any other exception: sets status='failed', stores error in log.

    Critical: each DB transaction opens a fresh connection and closes it immediately.
    Do NOT reuse a connection across the long pipeline run — it may go stale.
    """
    try:
        async with _semaphore:
            # ----------------------------------------------------------------
            # Transition: pending -> running
            # ----------------------------------------------------------------
            db = await get_db()
            try:
                await db.execute("BEGIN IMMEDIATE")
                await db.execute(
                    "UPDATE jobs SET status='running', updated_at=? WHERE id=?",
                    (_now_iso(), job_id),
                )
                await db.commit()
            finally:
                await db.close()

            await _push_event(
                job_id,
                "status",
                {"id": job_id, "status": "running", "updated_at": _now_iso()},
            )

            # ----------------------------------------------------------------
            # Load base CV (sync disk read + YAML parse — run in thread pool)
            # ----------------------------------------------------------------
            base_cv = await asyncio.to_thread(load_base_cv)

            # ----------------------------------------------------------------
            # Run AI pipeline (Claude CLI via subprocess — async wrapper)
            # ----------------------------------------------------------------
            tailored_cv, gap_diff = await run_pipeline_async(base_cv, job_text)

            # ----------------------------------------------------------------
            # Render LaTeX source (sync Jinja2 string templating — fast, no I/O)
            # ----------------------------------------------------------------
            latex_source = render_latex(tailored_cv)

            # ----------------------------------------------------------------
            # Compile PDF (latexmk via subprocess — async wrapper)
            # ----------------------------------------------------------------
            pdf_bytes = await render_pdf_async(latex_source)

            # ----------------------------------------------------------------
            # Save PDF to disk
            # ----------------------------------------------------------------
            out_dir = Path("output") / company_name
            out_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = out_dir / f"{job_id}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            logger.info("Job %s: PDF saved to %s", job_id, pdf_path)

            # ----------------------------------------------------------------
            # Transition: running -> complete; persist results
            # ----------------------------------------------------------------
            db = await get_db()
            try:
                await db.execute("BEGIN IMMEDIATE")
                await db.execute(
                    """UPDATE jobs
                       SET status='complete', tailored_cv_json=?, gap_diff_json=?,
                           pdf_path=?, updated_at=?
                       WHERE id=?""",
                    (
                        tailored_cv.model_dump_json(),
                        json.dumps([g.model_dump() for g in gap_diff]),
                        str(pdf_path),
                        _now_iso(),
                        job_id,
                    ),
                )
                await db.commit()
            finally:
                await db.close()

            full_result = {
                "id": job_id,
                "status": "complete",
                "tailored_cv": tailored_cv.model_dump(),
                "gap_diff": [g.model_dump() for g in gap_diff],
                "pdf_url": f"/api/jobs/{job_id}/pdf",
            }
            await _push_event(job_id, "complete", full_result)
            logger.info("Job %s complete", job_id)

    except asyncio.CancelledError:
        logger.warning("Job %s cancelled", job_id)
        db = await get_db()
        try:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute(
                "UPDATE jobs SET status='cancelled', updated_at=? WHERE id=?",
                (_now_iso(), job_id),
            )
            await db.commit()
        except Exception:
            logger.exception("Failed to update cancelled status for job %s", job_id)
        finally:
            await db.close()

        await _push_event(
            job_id,
            "status",
            {"id": job_id, "status": "cancelled", "updated_at": _now_iso()},
        )
        raise  # MUST re-raise CancelledError — asyncio cancellation contract

    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        db = await get_db()
        try:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute(
                "UPDATE jobs SET status='failed', updated_at=? WHERE id=?",
                (_now_iso(), job_id),
            )
            await db.commit()
        except Exception:
            logger.exception("Failed to update failed status for job %s", job_id)
        finally:
            await db.close()

        await _push_event(
            job_id,
            "status",
            {"id": job_id, "status": "failed", "updated_at": _now_iso()},
        )

    finally:
        # Always remove from task registry so DELETE endpoint sees stale tasks correctly
        _job_tasks.pop(job_id, None)
