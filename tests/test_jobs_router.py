"""Integration tests for backend/routers/jobs.py — all six job lifecycle endpoints.

Tests exercise the HTTP layer using starlette.testclient.TestClient with:
- Mocked job_worker to avoid actual pipeline execution
- Isolated test database via patched backend.db.DB_PATH
- Direct DB row insertion for tests requiring pre-existing state

Follows project pattern: sync test functions, asyncio.run() for async setup.
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from backend.main import app


# ---------------------------------------------------------------------------
# Test DB helpers
# ---------------------------------------------------------------------------


async def _insert_job_row(
    db_path: Path,
    job_id: str,
    company: str = "TestCo",
    job_text: str = "test job text",
    status: str = "pending",
    pdf_path: str | None = None,
    tailored_cv_json: str | None = None,
    cv_history_json: str | None = None,
) -> None:
    """Insert a job row directly into the test database."""
    from datetime import datetime, timezone

    from backend.db import get_db

    db = await get_db(db_path)
    try:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "INSERT INTO jobs (id, company_name, job_text, status, pdf_path, tailored_cv_json, "
            "cv_history_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                job_id,
                company,
                job_text,
                status,
                pdf_path,
                tailored_cv_json,
                cv_history_json,
                now,
                now,
            ),
        )
        await db.commit()
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# No-op worker (used to prevent actual pipeline execution)
# ---------------------------------------------------------------------------


async def _noop_worker(*args, **kwargs) -> None:
    """Fake job worker that does nothing — used to keep jobs in 'pending' state."""
    pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_job_returns_201(tmp_path: Path):
    """POST /api/jobs/ returns 201 with job ID and status='pending'."""
    test_db = tmp_path / "test.db"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        response = client.post(
            "/api/jobs",
            json={"company_name": "TestCo", "job_link": "https://example.com/test", "job_text": "Looking for Python dev"},
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["company_name"] == "TestCo"
    # Verify ID looks like a UUID (not empty)
    assert len(data["id"]) > 0


def test_create_job_missing_field_returns_422(tmp_path: Path):
    """POST /api/jobs/ with missing required field returns 422 Unprocessable Entity."""
    test_db = tmp_path / "test.db"

    with (
        patch("backend.db.DB_PATH", test_db),
        TestClient(app) as client,
    ):
        # Missing required 'job_text' field
        response = client.post(
            "/api/jobs",
            json={"company_name": "TestCo"},
        )

    assert response.status_code == 422


def test_list_jobs_returns_array(tmp_path: Path):
    """GET /api/jobs/ returns a list with at least the jobs that were created."""
    test_db = tmp_path / "test.db"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        # POST two jobs
        client.post(
            "/api/jobs",
            json={"company_name": "CompanyA", "job_link": "https://example.com/a", "job_text": "Job listing A"},
        )
        client.post(
            "/api/jobs",
            json={"company_name": "CompanyB", "job_link": "https://example.com/b", "job_text": "Job listing B"},
        )

        # GET all jobs
        response = client.get("/api/jobs")

    assert response.status_code == 200
    jobs = response.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 2


def test_get_job_detail_returns_job(tmp_path: Path):
    """GET /api/jobs/{id} returns the job matching the ID."""
    test_db = tmp_path / "test.db"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        # Create a job first
        create_response = client.post(
            "/api/jobs",
            json={"company_name": "DetailCo", "job_link": "https://example.com/detail", "job_text": "Detailed job listing"},
        )
        assert create_response.status_code == 201
        job_id = create_response.json()["id"]

        # Fetch it by ID
        response = client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["status"] == "pending"
    assert data["company_name"] == "DetailCo"


def test_get_job_detail_404_for_missing(tmp_path: Path):
    """GET /api/jobs/{id} returns 404 for non-existent job ID."""
    test_db = tmp_path / "test.db"

    with (
        patch("backend.db.DB_PATH", test_db),
        TestClient(app) as client,
    ):
        response = client.get(f"/api/jobs/{uuid.uuid4()}")

    assert response.status_code == 404


def test_delete_job_returns_204(tmp_path: Path):
    """DELETE /api/jobs/{id} returns 204 for a pending job."""
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    with (
        patch("backend.db.DB_PATH", test_db),
        TestClient(app) as client,
    ):
        # DB is now initialized by lifespan — insert directly
        asyncio.run(_insert_job_row(test_db, job_id, status="pending"))
        response = client.delete(f"/api/jobs/{job_id}")

    # 204 No Content — job was pending (no active task, but status is non-terminal)
    assert response.status_code == 204


def test_delete_job_409_for_completed(tmp_path: Path):
    """DELETE /api/jobs/{id} returns 409 when job is already complete."""
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    with (
        patch("backend.db.DB_PATH", test_db),
        TestClient(app) as client,
    ):
        # DB is now initialized by lifespan — insert directly
        asyncio.run(_insert_job_row(test_db, job_id, status="complete"))
        response = client.delete(f"/api/jobs/{job_id}")

    assert response.status_code == 409


def test_delete_job_404_for_missing(tmp_path: Path):
    """DELETE /api/jobs/{id} returns 404 for non-existent job ID."""
    test_db = tmp_path / "test.db"

    with (
        patch("backend.db.DB_PATH", test_db),
        TestClient(app) as client,
    ):
        response = client.delete(f"/api/jobs/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_pdf_404_when_not_complete(tmp_path: Path):
    """GET /api/jobs/{id}/pdf returns 404 when job is still pending."""
    test_db = tmp_path / "test.db"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        # Create a job — worker is mocked so it stays pending
        create_response = client.post(
            "/api/jobs",
            json={"company_name": "PDFCo", "job_link": "https://example.com/pdf", "job_text": "PDF test job"},
        )
        assert create_response.status_code == 201
        job_id = create_response.json()["id"]

        # PDF should not be available yet
        response = client.get(f"/api/jobs/{job_id}/pdf")

    assert response.status_code == 404


def test_get_pdf_returns_bytes_when_complete(tmp_path: Path):
    """GET /api/jobs/{id}/pdf returns raw PDF bytes for a completed job."""
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    # Create a temp PDF file
    pdf_file = tmp_path / f"{job_id}.pdf"
    pdf_file.write_bytes(b"%PDF-test")

    with (
        patch("backend.db.DB_PATH", test_db),
        TestClient(app) as client,
    ):
        # DB is now initialized by lifespan — insert the completed job row
        asyncio.run(
            _insert_job_row(
                test_db,
                job_id,
                status="complete",
                pdf_path=str(pdf_file),
            )
        )

        response = client.get(f"/api/jobs/{job_id}/pdf")

    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert response.content == b"%PDF-test"

    # Cleanup
    pdf_file.unlink(missing_ok=True)


def test_regenerate_job_archives_versioned_pdf(tmp_path: Path):
    """Regenerating a job creates a versioned copy of the existing PDF and tex,

    ensuring older versions download the original content rather than the new PDF.
    """
    import json
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    pdf_file = tmp_path / f"{job_id}.pdf"
    pdf_file.write_bytes(b"%PDF-version-1")
    tex_file = tmp_path / f"{job_id}.tex"
    tex_file.write_text(r"\documentclass{article} Version 1", encoding="utf-8")

    cv_data = {
        "contact": {"name": "Test Candidate", "email": "test@example.com"},
        "summary": "V1 summary",
        "experience": [],
        "skills": ["Python"],
        "education": [],
    }

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        asyncio.run(
            _insert_job_row(
                test_db,
                job_id,
                status="complete",
                pdf_path=str(pdf_file),
                tailored_cv_json=json.dumps(cv_data),
            )
        )

        # Trigger regeneration
        regen_resp = client.post(f"/api/jobs/{job_id}/regenerate", json={})
        assert regen_resp.status_code == 200
        data = regen_resp.json()
        assert data["status"] == "pending"
        assert len(data["cv_history"]) == 1
        assert data["cv_history"][0]["version"] == 1

        # Check that versioned PDF exists on disk with V1 bytes
        v1_pdf = tmp_path / f"{job_id}-v1.pdf"
        assert v1_pdf.exists(), "Versioned PDF was not created on disk"
        assert v1_pdf.read_bytes() == b"%PDF-version-1"

        # Check that versioned TeX exists on disk with V1 text
        v1_tex = tmp_path / f"{job_id}-v1.tex"
        assert v1_tex.exists(), "Versioned TeX was not created on disk"
        assert v1_tex.read_text(encoding="utf-8") == r"\documentclass{article} Version 1"

        # Simulate the background worker completing regeneration with new V2 content
        pdf_file.write_bytes(b"%PDF-version-2")

        # GET /api/jobs/{id}/pdf/1 should return Version 1 bytes, NOT Version 2
        v1_resp = client.get(f"/api/jobs/{job_id}/pdf/1")
        assert v1_resp.status_code == 200
        assert v1_resp.content == b"%PDF-version-1"


def test_delete_job_cleans_up_historical_pdf_and_tex(tmp_path: Path):
    """Permanently deleting a job removes the primary and all historical PDF/TeX files."""
    import json
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    pdf_file = tmp_path / f"{job_id}.pdf"
    pdf_file.write_bytes(b"%PDF-current")
    tex_file = tmp_path / f"{job_id}.tex"
    tex_file.write_text(r"Current tex", encoding="utf-8")

    v1_pdf = tmp_path / f"{job_id}-v1.pdf"
    v1_pdf.write_bytes(b"%PDF-v1")
    v1_tex = tmp_path / f"{job_id}-v1.tex"
    v1_tex.write_text(r"V1 tex", encoding="utf-8")

    history = [
        {"version": 1, "pdf_path": str(v1_pdf), "created_at": "2026-01-01T00:00:00Z"}
    ]

    with (
        patch("backend.db.DB_PATH", test_db),
        TestClient(app) as client,
    ):
        asyncio.run(
            _insert_job_row(
                test_db,
                job_id,
                status="complete",
                pdf_path=str(pdf_file),
                cv_history_json=json.dumps(history),
            )
        )

        del_resp = client.delete(f"/api/jobs/{job_id}/remove")
        assert del_resp.status_code == 204

    # Verify both current and historical files were deleted from disk
    assert not pdf_file.exists()
    assert not tex_file.exists()
    assert not v1_pdf.exists()
    assert not v1_tex.exists()

