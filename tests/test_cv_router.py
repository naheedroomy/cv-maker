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
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from backend.main import app

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

    updated_cv = {**_VALID_CV}
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
