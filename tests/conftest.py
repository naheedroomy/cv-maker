# tests/conftest.py
from pathlib import Path

import pytest

from cv_maker.models import TailoredCV

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


@pytest.fixture
def minimal_tailored_cv() -> TailoredCV:
    """Minimal valid TailoredCV — no special LaTeX characters."""
    return TailoredCV.model_validate(MINIMAL_CV)


@pytest.fixture
def tailored_cv_with_special_chars() -> TailoredCV:
    """TailoredCV with LaTeX special characters in several fields.

    Used to verify escape_latex is applied at the template boundary.
    Fields include &, %, _, $, # characters.
    """
    data = {
        "contact": {"name": "Jane O'Brien", "email": "jane@example.com"},
        "summary": "100% remote & distributed systems engineer.",
        "experience": [
            {
                "company": "Acme & Co",
                "title": "Senior Engineer",
                "start": "2021-06",
                "end": "2024-01",
                "bullets": [
                    "Reduced latency by 50% using C++ & Rust",
                    "Managed $2M budget for infrastructure",
                ],
            }
        ],
        "skills": ["Python", "C++", "Rust"],
        "education": [{"institution": "MIT", "degree": "BSc"}],
    }
    return TailoredCV.model_validate(data)
