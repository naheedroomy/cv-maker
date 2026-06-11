"""Tests for core/validation.py — post-generation TailoredCV validation."""
from __future__ import annotations

import pytest

from core.models import BaseCV, TailoredCV
from core.validation import validate_tailored_cv


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_base() -> BaseCV:
    return BaseCV.model_validate({
        "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
        "summary": "Experienced Python engineer.",
        "experience": [
            {
                "company": "TechCorp",
                "title": "Senior Software Engineer",
                "start": "2019-03",
                "end": "2024-01",
                "bullets": ["Built REST APIs with Python and FastAPI"],
                "technologies": ["Python", "FastAPI"],
            },
            {
                "company": "OldCo",
                "title": "Junior Developer",
                "start": "2017-01",
                "end": "2019-02",
                "bullets": ["Maintained internal tools"],
                "technologies": ["Python"],
            },
        ],
        "skills": ["Python", "FastAPI"],
        "education": [{"institution": "State University", "degree": "BSc", "field": "CS", "year": 2016}],
        "certifications": ["AWS Certified"],
        "languages": [{"language": "English", "level": "Native"}],
    })


def _make_tailored(base: BaseCV | None = None) -> TailoredCV:
    """Create a TailoredCV that matches the given BaseCV (or _make_base() default)."""
    if base is None:
        base = _make_base()
    return TailoredCV.model_validate(base.model_dump())


# ── Tests ────────────────────────────────────────────────────────────────────


class TestContactValidation:
    def test_matching_contact_passes(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        warnings = validate_tailored_cv(base, tailored)
        assert warnings == []

    def test_changed_name_fails(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        tailored.contact.name = "Different Name"
        with pytest.raises(ValueError, match="Contact field 'name' changed"):
            validate_tailored_cv(base, tailored)

    def test_changed_email_fails(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        tailored.contact.email = "other@example.com"
        with pytest.raises(ValueError, match="Contact field 'email' changed"):
            validate_tailored_cv(base, tailored)


class TestExperienceValidation:
    def test_role_count_match_passes(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        warnings = validate_tailored_cv(base, tailored)
        assert warnings == []

    def test_role_count_mismatch_fails(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        # Remove one experience entry
        tailored.experience = tailored.experience[:1]
        with pytest.raises(ValueError, match="Experience role count changed"):
            validate_tailored_cv(base, tailored)

    def test_company_name_changed_fails(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        tailored.experience[0].company = "NewCorp"
        with pytest.raises(ValueError, match="Company names changed"):
            validate_tailored_cv(base, tailored)

    def test_job_title_changed_is_corrected_and_warns(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        original_title = tailored.experience[0].title
        tailored.experience[0].title = "Principal Engineer"
        warnings = validate_tailored_cv(base, tailored)
        # Title is reset to the base CV value
        assert tailored.experience[0].title == original_title
        # A warning is emitted
        assert len(warnings) >= 1
        assert any("Title corrected" in w for w in warnings)
        assert any("Principal Engineer" in w for w in warnings)

    def test_date_changed_fails(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        tailored.experience[0].start = "2020-01"
        with pytest.raises(ValueError, match="Date changed"):
            validate_tailored_cv(base, tailored)

    def test_same_company_different_titles_no_false_correction(self) -> None:
        """Regression: two roles at the same company with different titles and
        date ranges should validate without changing either title."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Experienced engineer.",
            "experience": [
                {
                    "company": "TechCorp",
                    "title": "Senior Software Engineer",
                    "start": "2019-03",
                    "end": "2021-06",
                    "bullets": ["Built REST APIs"],
                    "technologies": ["Python"],
                },
                {
                    "company": "TechCorp",
                    "title": "Staff Engineer",
                    "start": "2021-07",
                    "end": "2024-01",
                    "bullets": ["Led platform team"],
                    "technologies": ["Python"],
                },
            ],
            "skills": ["Python"],
            "education": [{"institution": "State University", "degree": "BSc", "field": "CS", "year": 2016}],
            "certifications": ["AWS Certified"],
            "languages": [{"language": "English", "level": "Native"}],
        })
        tailored = TailoredCV.model_validate(base.model_dump())
        warnings = validate_tailored_cv(base, tailored)
        # Neither title should be corrected since they match the base.
        assert warnings == []

    def test_same_company_drift_only_affected_role_corrected(self) -> None:
        """Drift case: two roles at the same company; only the drifted role
        gets corrected to its own base title, not the other role's title."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Experienced engineer.",
            "experience": [
                {
                    "company": "TechCorp",
                    "title": "Senior Software Engineer",
                    "start": "2019-03",
                    "end": "2021-06",
                    "bullets": ["Built REST APIs"],
                    "technologies": ["Python"],
                },
                {
                    "company": "TechCorp",
                    "title": "Staff Engineer",
                    "start": "2021-07",
                    "end": "2024-01",
                    "bullets": ["Led platform team"],
                    "technologies": ["Python"],
                },
            ],
            "skills": ["Python"],
            "education": [{"institution": "State University", "degree": "BSc", "field": "CS", "year": 2016}],
            "certifications": ["AWS Certified"],
            "languages": [{"language": "English", "level": "Native"}],
        })
        tailored = TailoredCV.model_validate(base.model_dump())
        # Drift only the first role's title
        tailored.experience[0].title = "Principal Engineer"
        warnings = validate_tailored_cv(base, tailored)
        # First role corrected back to its own base title
        assert tailored.experience[0].title == "Senior Software Engineer"
        # Second role untouched — not overwritten by the first role's title
        assert tailored.experience[1].title == "Staff Engineer"
        # Warning emitted for the correction
        assert len(warnings) >= 1
        assert any("Title corrected" in w for w in warnings)
        assert any("Principal Engineer" in w for w in warnings)


class TestEducationValidation:
    def test_education_count_mismatch_fails(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        tailored.education.append(
            TailoredCV.model_fields["education"].annotation.__args__[0].model_validate(
                {"institution": "Fake U", "degree": "PhD"}
            )
        )
        with pytest.raises(ValueError, match="Education entries count changed"):
            validate_tailored_cv(base, tailored)

    def test_institution_changed_fails(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        tailored.education[0].institution = "Different School"
        with pytest.raises(ValueError, match="Education institutions changed"):
            validate_tailored_cv(base, tailored)


class TestCertificationValidation:
    def test_dropped_cert_fails(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        tailored.certifications = []
        with pytest.raises(ValueError, match="Certifications dropped"):
            validate_tailored_cv(base, tailored)


class TestLanguageValidation:
    def test_language_changed_fails(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        tailored.languages[0].level = "B1"
        with pytest.raises(ValueError, match="Languages changed"):
            validate_tailored_cv(base, tailored)


class TestSoftWarnings:
    def test_no_warnings_for_clean_tailored(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        warnings = validate_tailored_cv(base, tailored)
        assert warnings == []

    def test_invented_metric_triggers_warning(self) -> None:
        base = _make_base()
        tailored = _make_tailored(base)
        tailored.experience[0].bullets = [
            "Built REST APIs serving 10M requests/day with Python and FastAPI",
            "Managed 40+ EC2 instances",  # not in base
        ]
        warnings = validate_tailored_cv(base, tailored)
        assert len(warnings) > 0
        assert any("40+" in w for w in warnings)
