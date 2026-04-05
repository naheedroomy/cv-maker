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
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.db import get_db
from backend.pipeline_runner import render_pdf_async, run_provider_async
from cv_maker.data import load_base_cv
from cv_maker.providers import get_provider
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


async def job_worker(
    job_id: str, company_name: str, job_text: str, model: str = "claude-haiku"
) -> None:
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
    job_start = time.monotonic()
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
            t0 = time.monotonic()
            base_cv = await asyncio.to_thread(load_base_cv)
            logger.info("Job %s: [1/4] Base CV loaded (%.1fs)", job_id, time.monotonic() - t0)

            # ----------------------------------------------------------------
            # Run AI pipeline (provider-routed via async wrapper)
            # ----------------------------------------------------------------
            t0 = time.monotonic()
            provider = get_provider(model)
            logger.info("Job %s: [2/4] Starting %s pipeline...", job_id, type(provider).__name__)
            tailored_cv, gap_diff = await run_provider_async(provider, base_cv, job_text)
            logger.info(
                "Job %s: [2/4] %s pipeline done (%.1fs)",
                job_id, type(provider).__name__, time.monotonic() - t0,
            )

            # ----------------------------------------------------------------
            # Render LaTeX source (sync Jinja2 string templating — fast, no I/O)
            # ----------------------------------------------------------------
            t0 = time.monotonic()
            latex_source = render_latex(tailored_cv)
            logger.info("Job %s: [3/4] LaTeX rendered (%.1fs)", job_id, time.monotonic() - t0)

            # ----------------------------------------------------------------
            # Compile PDF (latexmk via subprocess — async wrapper)
            # ----------------------------------------------------------------
            t0 = time.monotonic()
            logger.info("Job %s: [4/4] Compiling PDF with latexmk...", job_id)
            pdf_bytes = await render_pdf_async(latex_source)
            logger.info(
                "Job %s: [4/4] PDF compiled (%.1fs, %d bytes)",
                job_id, time.monotonic() - t0, len(pdf_bytes),
            )

            # ----------------------------------------------------------------
            # Save outputs to disk
            # ----------------------------------------------------------------
            out_dir = Path("output") / company_name
            out_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = out_dir / f"{job_id}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            tex_path = out_dir / f"{job_id}.tex"
            tex_path.write_text(latex_source, encoding="utf-8")
            logger.info("Job %s: Files saved to %s", job_id, out_dir)

            # ----------------------------------------------------------------
            # Transition: running -> complete; persist results
            # ----------------------------------------------------------------
            _completed_at = _now_iso()
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
                        _completed_at,
                        job_id,
                    ),
                )
                await db.commit()
            finally:
                await db.close()

            full_result = {
                "id": job_id,
                "status": "complete",
                "company_name": company_name,
                "model": model,
                "created_at": None,      # not in local scope; frontend self-corrects via 30s poll
                "updated_at": _completed_at,
                "tailored_cv": tailored_cv.model_dump(),
                "gap_diff": [g.model_dump() for g in gap_diff],
                "pdf_url": f"/api/jobs/{job_id}/pdf",
            }
            await _push_event(job_id, "complete", full_result)
            total = time.monotonic() - job_start
            logger.info("Job %s: COMPLETE in %.1fs total", job_id, total)

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
