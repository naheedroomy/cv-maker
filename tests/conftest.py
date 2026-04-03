# tests/conftest.py
from pathlib import Path

import pytest

MINIMAL_CV = {
    "contact": {"name": "Test User", "email": "test@example.com"},
    "summary": "A test CV.",
    "experience": [
        {
            "company": "ACME",
            "title": "Engineer",
            "start": "2020-01",
            "bullets": ["Did things"],
        }
    ],
    "skills": ["Python"],
    "education": [{"institution": "State University", "degree": "BSc"}],
}


@pytest.fixture
def minimal_cv_dict():
    """Minimal valid BaseCV dict — satisfies all required fields."""
    return MINIMAL_CV.copy()


@pytest.fixture
def base_cv_path():
    """Path to the sample base_cv.yaml at project root."""
    return Path("base_cv.yaml")
