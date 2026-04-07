# tests/conftest.py
from pathlib import Path

import pytest

from cv_maker.models import BaseCV, TailoredCV

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


@pytest.fixture
def tailored_cv_with_competencies() -> TailoredCV:
    """TailoredCV with core_competencies populated — for pill rendering tests."""
    data = {
        **MINIMAL_CV,
        "core_competencies": [
            "Cloud Infrastructure",
            "CI/CD Pipelines",
            "Python & FastAPI",
            "Microservices",
        ],
    }
    return TailoredCV.model_validate(data)


@pytest.fixture
def base_cv() -> BaseCV:
    """Minimal BaseCV instance for pipeline tests — no filesystem dependency."""
    return BaseCV.model_validate({
        "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
        "summary": "Experienced Python engineer with 8 years in backend development.",
        "experience": [
            {
                "company": "TechCorp",
                "title": "Senior Software Engineer",
                "start": "2019-03",
                "end": "2024-01",
                "bullets": [
                    "Built REST APIs serving 10M requests/day using Python and FastAPI",
                    "Reduced database query latency by 40% via query optimization",
                ],
                "technologies": ["Python", "FastAPI", "PostgreSQL", "Redis"],
            }
        ],
        "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
        "education": [
            {"institution": "State University", "degree": "BSc", "field": "Computer Science", "year": 2016}
        ],
    })


@pytest.fixture
def sample_job_text() -> str:
    """Simulated job listing string for pipeline tests."""
    return (
        "We are looking for a Senior Backend Engineer to join our platform team. "
        "The ideal candidate has strong experience with Python, FastAPI, and PostgreSQL. "
        "You will design and build high-performance REST APIs and optimize database queries. "
        "Experience with Docker and Kubernetes is a plus."
    )
