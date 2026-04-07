"""Unit tests for backend/worker.py — job worker coroutine behavior.

Tests mock the pipeline and renderer to avoid actual Claude CLI and LaTeX calls.
All tests use real SQLite databases via tmp_path for proper isolation.
All tests follow project pattern: sync functions wrapping asyncio.run().
"""
from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db import get_db, init_db


# ---------------------------------------------------------------------------
# Fake model helpers
# ---------------------------------------------------------------------------


def _fake_base_cv():
    from cv_maker.models import BaseCV, ContactInfo, EducationItem, ExperienceItem

    return BaseCV(
        contact=ContactInfo(name="Test User", email="test@test.com"),
        summary="Test summary",
        experience=[
            ExperienceItem(
                company="TestCo",
                title="Dev",
                start="2020-01",
                bullets=["Did stuff"],
            )
        ],
        skills=["Python"],
        education=[EducationItem(institution="Uni", degree="BS")],
    )


def _fake_tailored_cv():
    from cv_maker.models import ContactInfo, EducationItem, ExperienceItem, TailoredCV

    return TailoredCV(
        contact=ContactInfo(name="Test User", email="test@test.com"),
        summary="Tailored summary",
        experience=[
            ExperienceItem(
                company="TestCo",
                title="Dev",
                start="2020-01",
                bullets=["Delivered stuff"],
            )
        ],
        skills=["Python"],
        education=[EducationItem(institution="Uni", degree="BS")],
    )


def _fake_gap_items():
    from cv_maker.models import GapItem

    return [GapItem(requirement="Python", match_level="strong", evidence="5 years exp")]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _init_test_db(db_path: Path) -> Path:
    """Initialize a fresh SQLite test database."""
    await init_db(db_path)
    return db_path


async def _insert_pending_job(
    db_path: Path,
    job_id: str,
    company: str = "TestCo",
    job_text: str = "test job text",
) -> None:
    """Insert a pending job row into the test database."""
    db = await get_db(db_path)
    try:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "INSERT INTO jobs (id, company_name, job_text, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?)",
            (job_id, company, job_text, now, now),
        )
        await db.commit()
    finally:
        await db.close()


async def _get_job_row(db_path: Path, job_id: str) -> dict:
    """Fetch a job row from the test database as a dict."""
    db = await get_db(db_path)
    try:
        cursor = await db.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_worker_semaphore_limits_concurrency():
    """Semaphore value must be exactly 5 — limits to 5 concurrent pipeline runs."""
    from backend.worker import _semaphore

    assert _semaphore._value == 5


def test_worker_completes_job_successfully(tmp_path: Path):
    """Worker transitions job to complete and saves PDF, tailored_cv, and gap_diff."""
    job_id = "test-job-complete-001"
    test_db = tmp_path / "test.db"
    out_dir = tmp_path / "output"

    async def _run():
        await _init_test_db(test_db)
        await _insert_pending_job(test_db, job_id)

        import backend.worker as worker_module

        fake_tailored = _fake_tailored_cv()
        fake_gaps = _fake_gap_items()

        async def fake_get_db(db_path=None):
            return await get_db(test_db)

        with (
            patch("backend.worker.get_db", side_effect=fake_get_db),
            patch(
                "backend.worker.load_base_cv",
                return_value=_fake_base_cv(),
            ),
            patch(
                "backend.worker.run_provider_async",
                new_callable=AsyncMock,
                return_value=(fake_tailored, fake_gaps),
            ),
            patch(
                "backend.worker.render_latex",
                return_value="\\documentclass{article}\\begin{document}test\\end{document}",
            ),
            patch(
                "backend.worker.render_pdf_async",
                new_callable=AsyncMock,
                return_value=b"%PDF-fake-content",
            ),
            patch.object(
                worker_module,
                "Path",
                side_effect=lambda p: out_dir if p == "output" else Path(p),
            ),
        ):
            await worker_module.job_worker(job_id, "TestCo", "test job text")

        row = await _get_job_row(test_db, job_id)
        assert row["status"] == "complete", f"Expected 'complete', got {row['status']}"
        assert row["tailored_cv_json"] is not None
        assert row["gap_diff_json"] is not None
        assert row["pdf_path"] is not None

        # Verify the tailored_cv_json is valid JSON
        tailored = json.loads(row["tailored_cv_json"])
        assert tailored["summary"] == "Tailored summary"

        # Verify gap_diff_json is valid JSON list
        gaps = json.loads(row["gap_diff_json"])
        assert len(gaps) == 1
        assert gaps[0]["requirement"] == "Python"

    asyncio.run(_run())

    # Cleanup
    if out_dir.exists():
        shutil.rmtree(out_dir)


def test_worker_sets_failed_on_pipeline_error(tmp_path: Path):
    """Worker sets status='failed' when pipeline raises an exception."""
    job_id = "test-job-fail-001"
    test_db = tmp_path / "test.db"

    async def _run():
        await _init_test_db(test_db)
        await _insert_pending_job(test_db, job_id)

        import backend.worker as worker_module

        async def fake_get_db(db_path=None):
            return await get_db(test_db)

        with (
            patch("backend.worker.get_db", side_effect=fake_get_db),
            patch(
                "backend.worker.load_base_cv",
                return_value=_fake_base_cv(),
            ),
            patch(
                "backend.worker.run_provider_async",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Claude CLI failed"),
            ),
        ):
            await worker_module.job_worker(job_id, "TestCo", "test job text")

        row = await _get_job_row(test_db, job_id)
        assert row["status"] == "failed", f"Expected 'failed', got {row['status']}"

        # Task should have been cleaned up in finally block
        assert job_id not in worker_module._job_tasks

    asyncio.run(_run())


def test_worker_handles_cancellation(tmp_path: Path):
    """Worker catches CancelledError, sets status='cancelled', and re-raises."""
    job_id = "test-job-cancel-001"
    test_db = tmp_path / "test.db"

    async def _run():
        await _init_test_db(test_db)
        await _insert_pending_job(test_db, job_id)

        import backend.worker as worker_module

        async def fake_get_db(db_path=None):
            return await get_db(test_db)

        async def slow_pipeline(*args, **kwargs):
            await asyncio.sleep(60)  # Simulate long-running pipeline
            return (_fake_tailored_cv(), _fake_gap_items())

        with (
            patch("backend.worker.get_db", side_effect=fake_get_db),
            patch(
                "backend.worker.load_base_cv",
                return_value=_fake_base_cv(),
            ),
            patch(
                "backend.worker.run_provider_async",
                side_effect=slow_pipeline,
            ),
        ):
            task = asyncio.create_task(
                worker_module.job_worker(job_id, "TestCo", "test job text")
            )
            worker_module._job_tasks[job_id] = task

            # Let the task start running (enter semaphore, update to running, etc.)
            await asyncio.sleep(0)
            await asyncio.sleep(0)  # Extra tick to ensure running state

            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert task.cancelled(), "Task should be cancelled"

        row = await _get_job_row(test_db, job_id)
        assert row["status"] == "cancelled", f"Expected 'cancelled', got {row['status']}"

        # Task should have been cleaned up in finally block
        assert job_id not in worker_module._job_tasks

    asyncio.run(_run())


def test_worker_pushes_sse_events(tmp_path: Path):
    """Worker pushes SSE events to registered queues for running and complete states."""
    job_id = "test-job-sse-001"
    test_db = tmp_path / "test.db"
    out_dir = tmp_path / "output"

    async def _run():
        await _init_test_db(test_db)
        await _insert_pending_job(test_db, job_id)

        import backend.worker as worker_module

        async def fake_get_db(db_path=None):
            return await get_db(test_db)

        # Register a queue to receive SSE events
        q: asyncio.Queue = asyncio.Queue()
        worker_module._sse_queues[job_id] = {q}

        try:
            with (
                patch("backend.worker.get_db", side_effect=fake_get_db),
                patch(
                    "backend.worker.load_base_cv",
                    return_value=_fake_base_cv(),
                ),
                patch(
                    "backend.worker.run_provider_async",
                    new_callable=AsyncMock,
                    return_value=(_fake_tailored_cv(), _fake_gap_items()),
                ),
                patch(
                    "backend.worker.render_latex",
                    return_value="\\documentclass{article}\\begin{document}test\\end{document}",
                ),
                patch(
                    "backend.worker.render_pdf_async",
                    new_callable=AsyncMock,
                    return_value=b"%PDF-fake-content",
                ),
                patch.object(
                    worker_module,
                    "Path",
                    side_effect=lambda p: out_dir if p == "output" else Path(p),
                ),
            ):
                await worker_module.job_worker(job_id, "TestCo", "test job text")

            # Drain the queue and collect all events
            events = []
            while not q.empty():
                events.append(q.get_nowait())

            # Assert at least one "running" status event
            running_events = [
                e for e in events
                if e.get("event") == "status" and e.get("data", {}).get("status") == "running"
            ]
            assert len(running_events) >= 1, (
                f"Expected at least one running status event, got events: {events}"
            )

            # Assert final "complete" event
            complete_events = [e for e in events if e.get("event") == "complete"]
            assert len(complete_events) >= 1, (
                f"Expected at least one complete event, got events: {events}"
            )

        finally:
            worker_module._sse_queues.pop(job_id, None)

    asyncio.run(_run())

    if out_dir.exists():
        shutil.rmtree(out_dir)
