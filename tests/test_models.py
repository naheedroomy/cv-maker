# tests/test_models.py
# Phase 1 success criteria verification.
# DATA-01: BaseCV loads from YAML and validates; invalid fields caught with clear errors.
# DATA-02: JobRequirements is importable, instantiable as a plain string wrapper.
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.data import load_base_cv
from core.models import BaseCV, EvidenceMap, EvidenceMatch, JobRequirements, TailoredCV

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


def test_base_cv_instantiable():
    """DATA-01: BaseCV is importable and instantiable with test data."""
    cv = BaseCV.model_validate(MINIMAL_CV)
    assert cv.contact.name == "Test User"
    assert cv.skills == ["Python"]
    assert cv.projects == []
    assert cv.certifications == []


def test_job_requirements_instantiable():
    """DATA-02: JobRequirements is a plain string wrapper — importable and instantiable."""
    jr = JobRequirements(raw_text="Senior Python Engineer at ACME Corp...")
    assert "Python" in jr.raw_text


def test_tailored_cv_importable():
    """TailoredCV is importable and instantiable with minimal data."""
    tcv = TailoredCV.model_validate(
        {
            "contact": {"name": "Test User", "email": "test@example.com"},
            "summary": "Tailored summary.",
            "experience": [],
            "skills": ["Python"],
            "education": [],
        }
    )
    assert tcv.summary == "Tailored summary."
    assert tcv.highlighted_technologies == []


def test_invalid_base_cv_raises_clear_error():
    """DATA-01: Invalid fields caught at validation time; error message names the bad field."""
    bad = {**MINIMAL_CV, "contact": {"email": "missing-name@example.com"}}  # name is required
    with pytest.raises(ValidationError) as exc_info:
        BaseCV.model_validate(bad)
    assert "name" in str(exc_info.value)


def test_load_base_cv_file_not_found():
    """load_base_cv raises FileNotFoundError for a missing path."""
    with pytest.raises(FileNotFoundError):
        load_base_cv(Path("nonexistent_cv_that_does_not_exist.yaml"))


def test_load_base_cv_success():
    """DATA-01: load_base_cv() loads data/base_cv.yaml and returns a valid BaseCV instance."""
    cv = load_base_cv(Path("data/base_cv.yaml"))
    assert cv.contact.name == "Naheed Roomy"
    assert "Python" in cv.skills
    assert len(cv.experience) >= 1


def test_load_base_cv_invalid_yaml_raises_runtime_error(tmp_path):
    """DATA-01: A YAML file failing Pydantic validation raises RuntimeError with clear prefix."""
    bad_yaml = tmp_path / "bad_cv.yaml"
    # Missing required 'name' field in contact
    bad_yaml.write_text(
        "contact:\n  email: test@example.com\n"
        "summary: test\nexperience: []\nskills: []\neducation: []\n"
    )
    with pytest.raises(RuntimeError) as exc_info:
        load_base_cv(bad_yaml)
    assert str(exc_info.value).startswith("base_cv.yaml failed validation:")


# ---------------------------------------------------------------------------
# Differentiator fields on EvidenceMatch (Tasks 5.1, 5.2, 5.3)
# ---------------------------------------------------------------------------


class TestEvidenceMatchDefaults:
    """Tests for optional differentiator/impact fields on EvidenceMatch."""

    def test_new_fields_default_to_empty_lists(self) -> None:
        """EvidenceMatch without new fields has empty lists, not None."""
        match = EvidenceMatch.model_validate({
            "requirement_phrase": "Python",
            "match_level": "strong",
            "evidence_text": "test",
        })
        assert match.differentiator_categories == []
        assert match.impact_signals == []

    def test_new_fields_preserved_in_output(self) -> None:
        """EvidenceMatch with new fields preserves them."""
        match = EvidenceMatch.model_validate({
            "requirement_phrase": "Kubernetes",
            "match_level": "strong",
            "evidence_text": "Managed clusters",
            "differentiator_categories": ["automation", "reliability"],
            "impact_signals": ["improved_consistency"],
        })
        assert match.differentiator_categories == ["automation", "reliability"]
        assert match.impact_signals == ["improved_consistency"]

    def test_evidence_map_with_differentiator_fields_serializes(self) -> None:
        """EvidenceMap with matches containing new fields serializes correctly."""
        em = EvidenceMap.model_validate({
            "matches": [{
                "requirement_phrase": "Python",
                "match_level": "strong",
                "evidence_text": "test",
                "allowed_keywords": ["Python"],
                "differentiator_categories": ["automation"],
                "impact_signals": ["standardized_process"],
            }],
            "pairing_plan": {"pairs": []},
            "coverage_summary": {"total_requirements": 1, "strong_matches": 1,
                                 "partial_matches": 0, "missing": 0},
        })
        data = em.model_dump()
        assert data["matches"][0]["differentiator_categories"] == ["automation"]
        assert data["matches"][0]["impact_signals"] == ["standardized_process"]
