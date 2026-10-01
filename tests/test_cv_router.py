"""Integration tests for backend/routers/cv.py — CV CRUD API endpoints.

Tests exercise the HTTP layer using starlette.testclient.TestClient with:
- Isolated test database via patched backend.db.DB_PATH
- No actual Gemini API calls (POST /upload is not tested here to avoid network calls)

Covers:
- GET /api/cv/me returns has_cv=false for new user (no CV saved)
- PUT /api/cv/me with valid BaseCV dict saves and GET returns it
- DELETE /api/cv/me removes the CV (returns has_cv=false)
- PUT /api/cv/me with invalid data returns 422
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from starlette.testclient import TestClient

from backend.main import app
from core.models import BaseCV

# A minimal but valid BaseCV dict for testing
_VALID_CV = {
    "contact": {
        "name": "Test User",
        "email": "test@example.com",
        "linkedin": None,
        "github": None,
        "phone": None,
        "location": "Sydney, Australia",
    },
    "summary": "Experienced software engineer with a passion for Python.",
    "experience": [
        {
            "company": "Acme Corp",
            "title": "Software Engineer",
            "location": "Sydney, Australia",
            "start": "2020-01",
            "end": None,
            "bullets": [
                "Built scalable microservices with Python and FastAPI.",
                "Led code reviews and mentored junior developers.",
            ],
            "technologies": ["Python", "FastAPI", "Docker"],
        }
    ],
    "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
    "education": [
        {
            "institution": "University of Sydney",
            "degree": "BSc",
            "field": "Computer Science",
            "year": 2018,
        }
    ],
    "projects": [],
    "certifications": [],
}


def test_get_cv_me_returns_no_cv_for_new_user(tmp_path: Path):
    """GET /api/cv/me returns has_cv=false for a user with no saved CV."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        response = client.get("/api/cv/me")

    assert response.status_code == 200
    data = response.json()
    assert data["has_cv"] is False
    assert data["cv"] is None


def test_put_cv_me_saves_cv(tmp_path: Path):
    """PUT /api/cv/me with a valid BaseCV dict saves the CV to DB."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        response = client.put("/api/cv/me", json=_VALID_CV)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "saved" in data["message"].lower()


def test_get_cv_me_returns_saved_cv(tmp_path: Path):
    """After PUT /api/cv/me, GET /api/cv/me returns the saved CV."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        # Save the CV
        put_response = client.put("/api/cv/me", json=_VALID_CV)
        assert put_response.status_code == 200

        # Retrieve it
        get_response = client.get("/api/cv/me")

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["has_cv"] is True
    assert data["cv"] is not None
    assert data["cv"]["contact"]["name"] == "Test User"
    assert data["cv"]["contact"]["email"] == "test@example.com"
    assert len(data["cv"]["experience"]) == 1
    assert data["cv"]["experience"][0]["company"] == "Acme Corp"
    assert len(data["cv"]["skills"]) == 4


def test_delete_cv_me_removes_cv(tmp_path: Path):
    """DELETE /api/cv/me removes the CV — GET /api/cv/me returns has_cv=false afterward."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        # Save first
        client.put("/api/cv/me", json=_VALID_CV)

        # Verify saved
        get_response = client.get("/api/cv/me")
        assert get_response.json()["has_cv"] is True

        # Delete
        delete_response = client.delete("/api/cv/me")
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["success"] is True

        # Verify removed
        get_after = client.get("/api/cv/me")

    assert get_after.status_code == 200
    assert get_after.json()["has_cv"] is False


def test_put_cv_me_with_invalid_data_returns_422(tmp_path: Path):
    """PUT /api/cv/me with invalid BaseCV data returns 422 Unprocessable Entity."""
    test_db = tmp_path / "test.db"

    invalid_cv = {
        "contact": {
            # Missing required 'email' field
            "name": "Test User",
        },
        "summary": "Test",
        # Missing required 'experience', 'skills', 'education'
    }

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        response = client.put("/api/cv/me", json=invalid_cv)

    assert response.status_code == 422


def test_crud_round_trip(tmp_path: Path):
    """Full CRUD round trip: save CV -> read CV -> update CV -> delete CV."""
    test_db = tmp_path / "test.db"

    updated_cv = dict(_VALID_CV)
    updated_cv["summary"] = "Updated summary for testing."

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        # 1. Initially no CV
        response = client.get("/api/cv/me")
        assert response.json()["has_cv"] is False

        # 2. Save initial CV
        client.put("/api/cv/me", json=_VALID_CV)

        # 3. Read back
        response = client.get("/api/cv/me")
        assert response.json()["has_cv"] is True
        assert response.json()["cv"]["summary"] == _VALID_CV["summary"]

        # 4. Update with new summary
        client.put("/api/cv/me", json=updated_cv)

        # 5. Read back updated
        response = client.get("/api/cv/me")
        assert response.json()["cv"]["summary"] == "Updated summary for testing."

        # 6. Delete
        client.delete("/api/cv/me")

        # 7. Verify removed
        response = client.get("/api/cv/me")
        assert response.json()["has_cv"] is False


def test_list_base_cvs(tmp_path: Path):
    """GET /api/cv/list returns list of BaseCvMeta ordered with default first."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        # User starts with seeded Main Base CV (default)
        list_res = client.get("/api/cv/list")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) >= 1
        assert items[0]["is_default"] is True
        assert items[0]["name"] == "Main Base CV"

        # Create a second non-default Base CV
        create_res = client.post(
            "/api/cv",
            json={"name": "Secondary Base CV", "cv": _VALID_CV, "is_default": False},
        )
        assert create_res.status_code == 200

        # Create a third Base CV marked as default
        create_res_default = client.post(
            "/api/cv",
            json={"name": "New Primary CV", "cv": _VALID_CV, "is_default": True},
        )
        assert create_res_default.status_code == 200
        new_primary_id = create_res_default.json()["id"]

        # Verify ordering: is_default first
        list_res = client.get("/api/cv/list")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) == 3
        assert items[0]["id"] == new_primary_id
        assert items[0]["is_default"] is True
        assert items[1]["is_default"] is False
        assert items[2]["is_default"] is False


def test_create_and_get_base_cv(tmp_path: Path):
    """POST /api/cv creates a new Base CV and GET /api/cv/{id} returns detail."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        create_res = client.post(
            "/api/cv",
            json={"name": "Backend Specialist", "cv": _VALID_CV, "is_default": False},
        )
        assert create_res.status_code == 200
        created = create_res.json()
        assert created["name"] == "Backend Specialist"
        assert created["is_default"] is False
        assert created["cv"]["contact"]["name"] == "Test User"
        cv_id = created["id"]

        # GET by ID
        get_res = client.get(f"/api/cv/{cv_id}")
        assert get_res.status_code == 200
        detail = get_res.json()
        assert detail["id"] == cv_id
        assert detail["name"] == "Backend Specialist"
        assert detail["cv"]["contact"]["name"] == "Test User"

        # Non-existent ID returns 404
        assert client.get("/api/cv/non-existent-id").status_code == 404


def test_duplicate_base_cv(tmp_path: Path):
    """POST /api/cv with source_id duplicates an existing Base CV."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        # Create an initial CV
        first_res = client.post(
            "/api/cv",
            json={"name": "Source CV", "cv": _VALID_CV, "is_default": False},
        )
        assert first_res.status_code == 200
        source_id = first_res.json()["id"]

        # Duplicate via source_id
        dup_res = client.post(
            "/api/cv",
            json={"name": "Duplicated CV", "source_id": source_id, "is_default": False},
        )
        assert dup_res.status_code == 200
        dup_data = dup_res.json()
        assert dup_data["name"] == "Duplicated CV"
        assert dup_data["id"] != source_id
        assert dup_data["cv"]["contact"]["name"] == "Test User"
        assert dup_data["cv"]["summary"] == _VALID_CV["summary"]

        # Duplicating non-existent source_id returns 404
        bad_res = client.post(
            "/api/cv",
            json={"name": "Fail CV", "source_id": "missing-uuid"},
        )
        assert bad_res.status_code == 404


def test_set_default_base_cv(tmp_path: Path):
    """PUT /api/cv/{id} with is_default=True promotes CV and unsets previous default."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        list_res = client.get("/api/cv/list")
        original_default_id = list_res.json()[0]["id"]

        create_res = client.post(
            "/api/cv",
            json={"name": "Second CV", "cv": _VALID_CV, "is_default": False},
        )
        second_id = create_res.json()["id"]

        # Set second CV as default
        put_res = client.put(f"/api/cv/{second_id}", json={"is_default": True})
        assert put_res.status_code == 200
        assert put_res.json()["is_default"] is True

        # Verify old default is no longer default
        old_default_detail = client.get(f"/api/cv/{original_default_id}").json()
        assert old_default_detail["is_default"] is False

        # Verify new default is reflected in list
        new_list = client.get("/api/cv/list").json()
        assert new_list[0]["id"] == second_id
        assert new_list[0]["is_default"] is True


def test_delete_base_cv_guard_last_one(tmp_path: Path):
    """DELETE /api/cv/{id} returns 400 when user has only 1 Base CV."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        items = client.get("/api/cv/list").json()
        assert len(items) == 1
        only_id = items[0]["id"]

        del_res = client.delete(f"/api/cv/{only_id}")
        assert del_res.status_code == 400
        assert "Cannot delete your only Base CV." in del_res.json()["detail"]


def test_delete_default_promotes_next_cv(tmp_path: Path):
    """When default Base CV is deleted, the next most recently updated is promoted."""
    test_db = tmp_path / "test.db"

    with patch("backend.db.DB_PATH", test_db), TestClient(app) as client:
        # Get seeded default
        initial_items = client.get("/api/cv/list").json()
        seeded_default_id = initial_items[0]["id"]

        # Create a second CV
        second_res = client.post(
            "/api/cv",
            json={"name": "Second CV", "cv": _VALID_CV, "is_default": False},
        )
        second_id = second_res.json()["id"]

        # Delete the seeded default CV
        del_res = client.delete(f"/api/cv/{seeded_default_id}")
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # Second CV must now be promoted to default
        remaining_items = client.get("/api/cv/list").json()
        assert len(remaining_items) == 1
        assert remaining_items[0]["id"] == second_id
        assert remaining_items[0]["is_default"] is True


def test_upload_base_cv_with_name_and_model(tmp_path: Path):
    """POST /api/cv/upload parses PDF with user key, saves with name, and returns base_cv_id."""
    test_db = tmp_path / "test.db"

    mock_parsed_cv = BaseCV.model_validate(_VALID_CV)

    with (
        patch("backend.db.DB_PATH", test_db),
        patch(
            "backend.routers.cv.parse_pdf_to_base_cv",
            new_callable=AsyncMock,
            return_value=mock_parsed_cv,
        ) as mock_parse,
        patch(
            "backend.routers.cv.get_api_key",
            new_callable=AsyncMock,
            return_value="mock-key-xyz",
        ) as mock_key,
        TestClient(app) as client,
    ):
        files = {"file": ("resume.pdf", b"%PDF-1.4 test resume content", "application/pdf")}
        data = {
            "name": "Fullstack Cloud Resume",
            "provider": "openai",
            "model": "gpt-4o",
        }
        res = client.post("/api/cv/upload", files=files, data=data)
        assert res.status_code == 200
        res_data = res.json()
        assert res_data["success"] is True
        assert res_data["base_cv_id"] is not None
        assert res_data["name"] == "Fullstack Cloud Resume"
        assert res_data["cv"]["contact"]["name"] == "Test User"

        mock_key.assert_called_once_with("openai_api_key", 1)
        mock_parse.assert_called_once_with(
            b"%PDF-1.4 test resume content",
            provider="openai",
            model="gpt-4o",
            api_key="mock-key-xyz",
        )

        # Verify saved in base_cvs
        get_res = client.get(f"/api/cv/{res_data['base_cv_id']}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Fullstack Cloud Resume"


def test_download_base_cv_by_id_pdf(tmp_path: Path):
    """POST /api/cv/{id}/pdf returns application/pdf with no-cache headers."""
    test_db = tmp_path / "test.db"

    mock_pdf_bytes = b"%PDF-1.4 fake generated pdf bytes"

    with (
        patch("backend.db.DB_PATH", test_db),
        patch("backend.routers.cv.render_latex", return_value="\\documentclass{article}"),
        patch("backend.routers.cv.render_pdf", return_value=mock_pdf_bytes),
        TestClient(app) as client,
    ):
        items = client.get("/api/cv/list").json()
        cv_id = items[0]["id"]

        # 1. Download by ID from DB (no body)
        pdf_res = client.post(f"/api/cv/{cv_id}/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.headers["cache-control"] == "no-cache, no-store, must-revalidate"
        assert pdf_res.content == mock_pdf_bytes

        # 2. Download with custom body override
        custom_cv = dict(_VALID_CV)
        custom_cv["contact"] = dict(_VALID_CV["contact"])
        custom_cv["contact"]["name"] = "Overridden Name"
        override_res = client.post(f"/api/cv/{cv_id}/pdf", json=custom_cv)
        assert override_res.status_code == 200
        assert override_res.headers["content-type"] == "application/pdf"
        assert override_res.content == mock_pdf_bytes

