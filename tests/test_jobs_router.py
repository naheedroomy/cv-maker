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
    base_cv_id: str | None = None,
    base_cv_name: str | None = None,
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
            "cv_history_json, base_cv_id, base_cv_name, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                job_id,
                company,
                job_text,
                status,
                pdf_path,
                tailored_cv_json,
                cv_history_json,
                base_cv_id,
                base_cv_name,
                now,
                now,
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def _insert_base_cv_row(
    db_path: Path,
    cv_id: str,
    user_id: int = 1,
    name: str = "Custom Base CV",
    cv_yaml: str | None = None,
    is_default: int = 0,
) -> None:
    """Insert a base_cvs row directly into the test database."""
    from datetime import datetime, timezone

    import yaml

    from backend.db import get_db

    if cv_yaml is None:
        cv_yaml = yaml.dump({
            "contact": {"name": f"Candidate for {name}", "email": "test@example.com"},
            "summary": f"Summary for {name}",
            "experience": [],
            "skills": ["Python"],
            "education": [],
        })
    db = await get_db(db_path)
    try:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "INSERT INTO base_cvs (id, user_id, name, cv_yaml, is_default, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cv_id, user_id, name, cv_yaml, is_default, now, now),
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


def test_regenerate_job_with_effort_model_and_notes(tmp_path: Path):
    """Regenerating a job with model override, effort level, and user notes updates job row."""
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

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
            )
        )

        regen_resp = client.post(
            f"/api/jobs/{job_id}/regenerate",
            json={
                "model": "claude-haiku",
                "model_id": "claude-3-7-sonnet-20250219",
                "reasoning_effort": "high",
                "creativity_level": 3,
                "user_notes": "replace GCP with AWS on HiAcuity work experience",
            },
        )
        assert regen_resp.status_code == 200
        data = regen_resp.json()
        assert data["status"] == "pending"
        assert data["model"] == "claude-haiku"
        assert data["model_id"] == "claude-3-7-sonnet-20250219"
        assert data["reasoning_effort"] == "high"
        assert data["creativity_level"] == 3
        assert data["user_notes"] == "replace GCP with AWS on HiAcuity work experience"


def test_regenerate_job_legacy_creativity_clamped(tmp_path: Path):
    """Regenerating an older job that had creativity_level=5 clamps creativity to 3."""
    from backend.db import get_db

    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    async def _insert_with_high_creativity() -> None:
        await _insert_job_row(test_db, job_id, status="complete")
        db = await get_db(test_db)
        try:
            await db.execute("UPDATE jobs SET creativity_level = 5 WHERE id = ?", (job_id,))
            await db.commit()
        finally:
            await db.close()

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        asyncio.run(_insert_with_high_creativity())

        regen_resp = client.post(f"/api/jobs/{job_id}/regenerate", json={})
        assert regen_resp.status_code == 200
        data = regen_resp.json()
        assert data["creativity_level"] == 3


def test_job_create_and_regenerate_creativity_validation(tmp_path: Path):
    """Creativity level > 3 is rejected with 422 Unprocessable Entity."""
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        asyncio.run(_insert_job_row(test_db, job_id, status="complete"))

        # Test job create rejects creativity_level=4
        create_resp = client.post(
            "/api/jobs",
            json={
                "company_name": "TestCo",
                "job_text": "Requirements here...",
                "creativity_level": 4,
            },
        )
        assert create_resp.status_code == 422

        # Test job regenerate rejects creativity_level=4
        regen_resp = client.post(
            f"/api/jobs/{job_id}/regenerate",
            json={"creativity_level": 4},
        )
        assert regen_resp.status_code == 422


def test_update_job_cv_success_archives_version_and_recompiles_pdf(tmp_path: Path):
    """PUT /api/jobs/{id}/cv updates tailored CV, archives previous version, and recompiles PDF."""
    import json
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    pdf_file = tmp_path / f"{job_id}.pdf"
    pdf_file.write_bytes(b"%PDF-original")
    tex_file = tmp_path / f"{job_id}.tex"
    tex_file.write_text(r"\documentclass{article} Original", encoding="utf-8")

    initial_cv = {
        "contact": {"name": "Test Candidate", "email": "test@example.com"},
        "summary": "Original summary",
        "experience": [
            {
                "company": "Old Corp",
                "title": "Engineer",
                "start": "2020-01",
                "end": "2022-01",
                "bullets": ["Original bullet 1"],
                "technologies": ["Python"],
            }
        ],
        "skills": ["Python"],
        "education": [],
        "projects": [],
        "certifications": [],
        "languages": [],
        "highlighted_technologies": [],
        "tailoring_notes": [],
    }

    updated_cv = {
        "contact": {"name": "Test Candidate", "email": "test@example.com"},
        "summary": "Modified summary by user",
        "experience": [
            {
                "company": "Old Corp",
                "title": "Senior Engineer",
                "start": "2020-01",
                "end": "2022-01",
                "bullets": ["Modified bullet 1", "Added bullet 2"],
                "technologies": ["Python", "Docker"],
            }
        ],
        "skills": ["Python", "Docker"],
        "education": [],
        "projects": [],
        "certifications": [],
        "languages": [],
        "highlighted_technologies": [],
        "tailoring_notes": [],
    }

    async def _mock_render_pdf_async(latex_src: str) -> bytes:
        return b"%PDF-recompiled"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.pipeline_runner.render_pdf_async", _mock_render_pdf_async),
        TestClient(app) as client,
    ):
        asyncio.run(
            _insert_job_row(
                test_db,
                job_id,
                status="complete",
                pdf_path=str(pdf_file),
                tailored_cv_json=json.dumps(initial_cv),
            )
        )

        resp = client.put(f"/api/jobs/{job_id}/cv", json=updated_cv)
        assert resp.status_code == 200
        data = resp.json()

        # Tailored CV updated
        assert data["tailored_cv"]["summary"] == "Modified summary by user"
        assert len(data["tailored_cv"]["experience"][0]["bullets"]) == 2

        # Version history archived
        assert len(data["cv_history"]) == 1
        assert data["cv_history"][0]["version"] == 1
        assert data["cv_history"][0]["tailored_cv"]["summary"] == "Original summary"

        # Versioned archive files exist
        v1_pdf = tmp_path / f"{job_id}-v1.pdf"
        assert v1_pdf.exists()
        assert v1_pdf.read_bytes() == b"%PDF-original"

        # Current PDF file updated with newly compiled bytes
        assert pdf_file.read_bytes() == b"%PDF-recompiled"


def test_update_job_cv_not_found(tmp_path: Path):
    """PUT /api/jobs/{id}/cv returns 404 for unknown job."""
    test_db = tmp_path / "test.db"
    missing_id = str(uuid.uuid4())

    with (
        patch("backend.db.DB_PATH", test_db),
        TestClient(app) as client,
    ):
        resp = client.put(
            f"/api/jobs/{missing_id}/cv",
            json={
                "contact": {"name": "Test", "email": "test@example.com"},
                "summary": "Summary",
                "experience": [],
                "skills": [],
                "education": [],
            },
        )
        assert resp.status_code == 404


def test_update_job_cv_not_complete_returns_400(tmp_path: Path):
    """PUT /api/jobs/{id}/cv returns 400 if job is still pending or running."""
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    with (
        patch("backend.db.DB_PATH", test_db),
        TestClient(app) as client,
    ):
        asyncio.run(
            _insert_job_row(
                test_db,
                job_id,
                status="running",
            )
        )

        resp = client.put(
            f"/api/jobs/{job_id}/cv",
            json={
                "contact": {"name": "Test", "email": "test@example.com"},
                "summary": "Summary",
                "experience": [],
                "skills": [],
                "education": [],
            },
        )
        assert resp.status_code == 400


def test_update_job_cv_preserves_added_skill_category_and_skills(tmp_path: Path):
    """PUT /api/jobs/{id}/cv preserves user-added skill category and skills even when
    the existing CV already had 15 skills.
    """
    import json
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())

    pdf_file = tmp_path / f"{job_id}.pdf"
    pdf_file.write_bytes(b"%PDF-original")
    tex_file = tmp_path / f"{job_id}.tex"
    tex_file.write_text(r"\documentclass{article} Original", encoding="utf-8")

    # 15 skills across 3 categories
    initial_skills = [
        "Cloud & Platforms: AWS, GCP, Azure, Docker, Kubernetes",
        "Languages: Python, TypeScript, JavaScript, Go, Rust",
        "Databases: PostgreSQL, MySQL, Redis, MongoDB, Cassandra",
    ]
    initial_cv = {
        "contact": {"name": "Test Candidate", "email": "test@example.com"},
        "summary": "Original summary",
        "experience": [],
        "skills": initial_skills,
        "education": [],
    }

    # User manually adds a 4th category with 2 skills (total 17 skills)
    updated_skills = initial_skills + ["Observability: Prometheus, Grafana"]
    updated_cv = {
        "contact": {"name": "Test Candidate", "email": "test@example.com"},
        "summary": "Original summary",
        "experience": [],
        "skills": updated_skills,
        "education": [],
    }

    captured_latex: list[str] = []

    async def _mock_render_pdf_async(latex_src: str) -> bytes:
        captured_latex.append(latex_src)
        return b"%PDF-recompiled-with-observability"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.pipeline_runner.render_pdf_async", _mock_render_pdf_async),
        TestClient(app) as client,
    ):
        asyncio.run(
            _insert_job_row(
                test_db,
                job_id,
                status="complete",
                pdf_path=str(pdf_file),
                tailored_cv_json=json.dumps(initial_cv),
            )
        )

        resp = client.put(f"/api/jobs/{job_id}/cv", json=updated_cv)
        assert resp.status_code == 200
        data = resp.json()

        # The new category and skills MUST be present in the response
        categories = [s.split(":", 1)[0].strip() for s in data["tailored_cv"]["skills"] if ":" in s]
        assert "Observability" in categories
        assert any("Prometheus" in s for s in data["tailored_cv"]["skills"])

        # The recompiled LaTeX MUST include the new category and skills
        assert len(captured_latex) == 1
        assert "Observability" in captured_latex[0]
        assert "Prometheus" in captured_latex[0]

        # PDF download MUST return the new PDF and disable browser caching
        pdf_resp = client.get(f"/api/jobs/{job_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.content == b"%PDF-recompiled-with-observability"
        assert "no-cache" in pdf_resp.headers.get("Cache-Control", "")


def test_create_job_with_specific_base_cv(tmp_path: Path):
    """POST /api/jobs with base_cv_id associates the job with that Base CV."""
    test_db = tmp_path / "test.db"
    cv_id = f"cv-{uuid.uuid4()}"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        asyncio.run(
            _insert_base_cv_row(
                test_db,
                cv_id=cv_id,
                name="DevOps Base CV",
                is_default=0,
            )
        )
        response = client.post(
            "/api/jobs",
            json={
                "company_name": "DevOpsCo",
                "job_text": "Need DevOps Engineer",
                "base_cv_id": cv_id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["base_cv_id"] == cv_id
        assert data["base_cv_name"] == "DevOps Base CV"

        # Also verify GET /api/jobs/{id} returns base_cv_id and base_cv_name
        detail_resp = client.get(f"/api/jobs/{data['id']}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["base_cv_id"] == cv_id
        assert detail_data["base_cv_name"] == "DevOps Base CV"


def test_create_job_defaults_to_default_base_cv(tmp_path: Path):
    """POST /api/jobs without base_cv_id selects the user's default Base CV."""
    test_db = tmp_path / "test.db"
    default_cv_id = f"cv-default-{uuid.uuid4()}"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        # Ensure only our custom default CV is marked is_default=1
        async def _setup_default_cv():
            from backend.db import get_db

            db = await get_db(test_db)
            try:
                await db.execute("UPDATE base_cvs SET is_default = 0")
                await db.commit()
            finally:
                await db.close()
            await _insert_base_cv_row(
                test_db,
                cv_id=default_cv_id,
                name="Platform Default CV",
                is_default=1,
            )

        asyncio.run(_setup_default_cv())

        response = client.post(
            "/api/jobs",
            json={
                "company_name": "DefaultCo",
                "job_text": "Need Platform Engineer",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["base_cv_id"] == default_cv_id
        assert data["base_cv_name"] == "Platform Default CV"


def test_create_job_invalid_base_cv_returns_404(tmp_path: Path):
    """POST /api/jobs with non-existent base_cv_id returns 404."""
    test_db = tmp_path / "test.db"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _noop_worker),
        TestClient(app) as client,
    ):
        response = client.post(
            "/api/jobs",
            json={
                "company_name": "GhostCo",
                "job_text": "Ghost requirements",
                "base_cv_id": "non-existent-base-cv-id",
            },
        )

        assert response.status_code == 404
        assert "Base CV not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_worker_uses_selected_base_cv(tmp_path: Path, monkeypatch):
    """job_worker loads the Base CV matching base_cv_id from base_cvs table."""
    import yaml

    from backend.db import init_db
    from backend.worker import job_worker
    from core.models import TailoredCV

    test_db = tmp_path / "test.db"
    monkeypatch.setenv("CV_MAKER_DB_PATH", str(test_db))
    await init_db(test_db)

    cv_id = "cv-special-test"
    custom_yaml = yaml.dump({
        "contact": {
            "name": "YAML Specialist Candidate",
            "email": "specialist@example.com",
            "location": "Remote",
        },
        "summary": "Specialist with deep YAML experience",
        "experience": [],
        "skills": ["Kubernetes", "Helm"],
        "education": [],
    })
    await _insert_base_cv_row(
        test_db,
        cv_id=cv_id,
        name="YAML Specialist",
        cv_yaml=custom_yaml,
        is_default=0,
    )

    job_id = str(uuid.uuid4())
    await _insert_job_row(
        test_db,
        job_id=job_id,
        company="SpecialistCo",
        job_text="Need specialist",
        status="pending",
        base_cv_id=cv_id,
        base_cv_name="YAML Specialist",
    )

    mock_provider = AsyncMock()
    tailored_result = TailoredCV(
        contact={"name": "YAML Specialist Candidate", "email": "specialist@example.com"},
        summary="Tailored specialist",
        experience=[],
        skills=["Kubernetes"],
        education=[],
    )
    mock_run_provider = AsyncMock(return_value=(tailored_result, []))
    mock_render_pdf = AsyncMock(return_value=b"%PDF-mock")

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.worker.get_provider", AsyncMock(return_value=mock_provider)),
        patch("backend.worker.run_provider_async", mock_run_provider),
        patch("backend.worker.render_latex", lambda cv: r"\documentclass{article}"),
        patch("backend.worker.render_pdf_async", mock_render_pdf),
    ):
        await job_worker(
            job_id=job_id,
            company_name="SpecialistCo",
            job_text="Need specialist",
            base_cv_id=cv_id,
        )

    mock_run_provider.assert_called_once()
    called_base_cv = mock_run_provider.call_args[0][1]
    assert called_base_cv.contact.name == "YAML Specialist Candidate"
    assert called_base_cv.summary == "Specialist with deep YAML experience"


def test_regenerate_allows_switching_base_cv(tmp_path: Path):
    """POST /api/jobs/{id}/regenerate with new base_cv_id switches Base CV."""
    test_db = tmp_path / "test.db"
    job_id = str(uuid.uuid4())
    cv_id_1 = f"cv-1-{uuid.uuid4()}"
    cv_id_2 = f"cv-2-{uuid.uuid4()}"

    captured_worker_calls = []

    async def _recording_worker(*args, **kwargs):
        captured_worker_calls.append((args, kwargs))

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.jobs.job_worker", _recording_worker),
        TestClient(app) as client,
    ):
        asyncio.run(
            _insert_base_cv_row(
                test_db,
                cv_id=cv_id_1,
                name="Base CV One",
                is_default=1,
            )
        )
        asyncio.run(
            _insert_base_cv_row(
                test_db,
                cv_id=cv_id_2,
                name="Base CV Two",
                is_default=0,
            )
        )
        asyncio.run(
            _insert_job_row(
                test_db,
                job_id=job_id,
                company="SwitchCo",
                job_text="Requirements...",
                status="complete",
                base_cv_id=cv_id_1,
                base_cv_name="Base CV One",
            )
        )

        regen_resp = client.post(
            f"/api/jobs/{job_id}/regenerate",
            json={"base_cv_id": cv_id_2},
        )
        assert regen_resp.status_code == 200
        data = regen_resp.json()
        assert data["base_cv_id"] == cv_id_2
        assert data["base_cv_name"] == "Base CV Two"

        # Check in DB
        async def _check_db():
            from backend.db import get_db

            db = await get_db(test_db)
            try:
                cursor = await db.execute(
                    "SELECT base_cv_id, base_cv_name FROM jobs WHERE id=?", (job_id,)
                )
                return await cursor.fetchone()
            finally:
                await db.close()

        row = asyncio.run(_check_db())
        assert row["base_cv_id"] == cv_id_2
        assert row["base_cv_name"] == "Base CV Two"

        # Check worker received base_cv_id="cv_id_2"
        assert len(captured_worker_calls) == 1
        _, kwargs = captured_worker_calls[0]
        assert kwargs.get("base_cv_id") == cv_id_2





