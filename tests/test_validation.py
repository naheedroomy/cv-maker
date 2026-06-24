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


# ---------------------------------------------------------------------------
# Keyword-stuffing validation tests (Task 3.5)
# ---------------------------------------------------------------------------


class TestKeywordStuffingValidation:
    """Tests for keyword-stuffing soft checks in validate_tailored_cv."""

    JD_KEYWORDS = ["Kubernetes", "Terraform", "AWS", "CI/CD", "Python", "Docker"]

    def _make_tailored_with_bullets(self, bullets: list[str]) -> TailoredCV:
        """Create a tailored CV with given bullets for testing."""
        return TailoredCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Experienced engineer.",
            "experience": [
                {
                    "company": "C",
                    "title": "T",
                    "start": "2020-01",
                    "bullets": bullets,
                    "technologies": ["Python", "Kubernetes"],
                },
            ],
            "skills": ["Python", "Kubernetes", "Terraform"],
            "education": [{"institution": "U", "degree": "B"}],
        })

    def test_bullet_with_3_keywords_triggers_warning(self) -> None:
        """Bullet with 3+ JD keywords triggers a warning."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = self._make_tailored_with_bullets([
            "Built Kubernetes clusters with Terraform and automated CI/CD pipelines using Python and AWS",
        ])
        warnings = validate_tailored_cv(base, tailored, jd_keywords=self.JD_KEYWORDS)
        stuffing_warnings = [w for w in warnings if "keyword" in w.lower()]
        assert len(stuffing_warnings) > 0

    def test_bullet_with_0_to_2_keywords_no_warning(self) -> None:
        """Bullet with 2 or fewer keywords does not trigger stuffing warning."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": ["Python", "Kubernetes", "Terraform"]}],
            "skills": ["Python", "Kubernetes", "Terraform"],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = self._make_tailored_with_bullets([
            "Built CI/CD pipelines with GitHub Actions, reducing deploy time by 70%",
        ])
        warnings = validate_tailored_cv(base, tailored, jd_keywords=self.JD_KEYWORDS)
        stuffing_warnings = [w for w in warnings if "keyword" in w.lower()]
        assert len(stuffing_warnings) == 0

    def test_bare_technology_list_triggers_warning(self) -> None:
        """Bullet that is just a comma-separated tech list triggers warning."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = self._make_tailored_with_bullets([
            "Used Kubernetes, Terraform, AWS, Docker, CI/CD",
        ])
        warnings = validate_tailored_cv(base, tailored, jd_keywords=self.JD_KEYWORDS)
        stuffing_warnings = [w for w in warnings if "keyword" in w.lower()]
        assert len(stuffing_warnings) > 0

    def test_action_verb_bullet_no_keyword_warning(self) -> None:
        """Bullet with action verb and keywords produces no keyword warning."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = self._make_tailored_with_bullets([
            "Designed and deployed Kubernetes clusters with Terraform, improving scalability",
        ])
        warnings = validate_tailored_cv(base, tailored, jd_keywords=["Kubernetes", "Terraform"])
        stuffing_warnings = [w for w in warnings if "keyword" in w.lower()]
        assert len(stuffing_warnings) == 0

    def test_unsubstantiated_skill_triggers_warning(self) -> None:
        """Skill not in base CV and not in bullets triggers warning."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": ["Python"]}],
            "skills": ["Python"],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = TailoredCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["Built REST APIs with Python"],
                            "technologies": ["Python"]}],
            "skills": ["Python", "ArgoCD"],  # ArgoCD has no base CV evidence
            "education": [{"institution": "U", "degree": "B"}],
        })
        warnings = validate_tailored_cv(base, tailored,
                                         jd_keywords=["Python", "ArgoCD", "GitOps"])
        stuffing_warnings = [w for w in warnings if "Unsubstantiated" in w or "keyword" in w.lower()]
        assert len(stuffing_warnings) > 0

    def test_verified_skill_no_warning(self) -> None:
        """Skill with base CV evidence produces no warning."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["Used Python daily"], "technologies": ["Python"]}],
            "skills": ["Python"],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = TailoredCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["Built Python applications"],
                            "technologies": ["Python"]}],
            "skills": ["Python"],
            "education": [{"institution": "U", "degree": "B"}],
        })
        warnings = validate_tailored_cv(base, tailored,
                                         jd_keywords=["Python"])
        stuffing_warnings = [w for w in warnings if "Unsubstantiated" in w]
        assert len(stuffing_warnings) == 0

    def test_keyword_overuse_across_bullets(self) -> None:
        """Keyword appearing in 4+ bullets triggers overuse warning."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [
                {"company": "C", "title": "T", "start": "2020-01",
                 "bullets": ["test1"], "technologies": []},
                {"company": "D", "title": "T2", "start": "2018-01", "end": "2019-12",
                 "bullets": ["test2"], "technologies": []},
            ],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = TailoredCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [
                {"company": "C", "title": "T", "start": "2020-01",
                 "bullets": [
                     "Built Kubernetes clusters",
                     "Managed Kubernetes deployments",
                     "Automated Kubernetes scaling",
                     "Monitored Kubernetes health",
                 ], "technologies": ["Kubernetes"]},
                {"company": "D", "title": "T2", "start": "2018-01", "end": "2019-12",
                 "bullets": ["Did other things"], "technologies": []},
            ],
            "skills": ["Kubernetes"],
            "education": [{"institution": "U", "degree": "B"}],
        })
        warnings = validate_tailored_cv(base, tailored,
                                         jd_keywords=["Kubernetes"])
        overuse_warnings = [w for w in warnings if "overused" in w.lower()]
        assert len(overuse_warnings) > 0

    def test_no_keyword_warnings_when_jd_keywords_none(self) -> None:
        """When jd_keywords is None, keyword checks are skipped entirely."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = self._make_tailored_with_bullets([
            "Kubernetes Terraform AWS CI/CD Python Docker all in one bullet",
        ])
        warnings = validate_tailored_cv(base, tailored)  # no jd_keywords
        stuffing_warnings = [w for w in warnings if "keyword" in w.lower()]
        assert len(stuffing_warnings) == 0

    def test_case_insensitive_keyword_matching(self) -> None:
        """Keyword matching is case-insensitive."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": ["Python", "Kubernetes", "Terraform"]}],
            "skills": ["Python", "Kubernetes", "Terraform"],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = self._make_tailored_with_bullets([
            "Built kubernetes clusters with terraform",
        ])
        warnings = validate_tailored_cv(base, tailored,
                                         jd_keywords=["Kubernetes", "Terraform", "AWS"])
        # "kubernetes" + "terraform" = 2 DJ keywords matched (case-insensitive)
        # AWS is not in the bullet, so only 2 distinct keywords — no stuffing warning
        stuffing_warnings = [w for w in warnings
                            if "keyword stuffing" in w.lower() and "3 distinct" in w.lower()]
        assert len(stuffing_warnings) == 0

    def test_alias_resolution_k8s(self) -> None:
        """K8s is resolved to kubernetes via alias map."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = self._make_tailored_with_bullets([
            "Managed K8s clusters with Terraform for infrastructure",
        ])
        # Only checking that normalization works — K8s + Kubernetes should match
        warnings = validate_tailored_cv(base, tailored,
                                         jd_keywords=["Kubernetes", "Terraform"])
        stuffing_warnings = [w for w in warnings
                            if "keyword stuffing" in w.lower() and "3 distinct" in w.lower()]
        assert len(stuffing_warnings) == 0  # only 2 distinct JD keywords

    def test_stem_based_matching(self) -> None:
        """Stemming normalizes deploy/deploying/deployment."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = self._make_tailored_with_bullets([
            "Deploying applications and managing deployments with Docker",
        ])
        # "deploying" and "deployments" should stem to same root as "deployment"
        warnings = validate_tailored_cv(base, tailored,
                                         jd_keywords=["deployment", "Docker"])
        stuffing_warnings = [w for w in warnings
                            if "keyword stuffing" in w.lower() and "3 distinct" in w.lower()]
        assert len(stuffing_warnings) == 0  # deploying/deployments same root

    def test_keyword_warnings_alongside_invented_metrics(self) -> None:
        """Keyword warnings coexist with invented-metric warnings."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["test"], "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = self._make_tailored_with_bullets([
            "Built Kubernetes, Terraform, AWS, CI/CD for 50+ services with 99.9% uptime",
        ])
        warnings = validate_tailored_cv(base, tailored,
                                         jd_keywords=["Kubernetes", "Terraform", "AWS", "CI/CD"])
        # Should have both keyword stuffing warnings AND invented metric warnings
        kw_warnings = [w for w in warnings if "keyword" in w.lower()]
        metric_warnings = [w for w in warnings if "metric" in w.lower()]
        assert len(kw_warnings) > 0
        assert len(metric_warnings) > 0


# ---------------------------------------------------------------------------
# Generic bullet validation tests (Task 4.6)
# ---------------------------------------------------------------------------


class TestGenericBulletValidation:
    """Tests for generic/low-substance bullet soft checks."""

    def _make_tailored(self, bullets: list[str], skills: list[str] | None = None) -> TailoredCV:
        return TailoredCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [
                {"company": "C", "title": "T", "start": "2020-01",
                 "bullets": bullets, "technologies": []},
                {"company": "D", "title": "T2", "start": "2018-01", "end": "2019-12",
                 "bullets": bullets, "technologies": []},
                {"company": "E", "title": "T3", "start": "2016-01", "end": "2017-12",
                 "bullets": bullets, "technologies": []},
            ],
            "skills": skills or ["Python"],
            "education": [{"institution": "U", "degree": "B"}],
        })

    def _make_base(self, bullets: list[str]) -> BaseCV:
        return BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [
                {"company": "C", "title": "T", "start": "2020-01",
                 "bullets": bullets, "technologies": []},
                {"company": "D", "title": "T2", "start": "2018-01", "end": "2019-12",
                 "bullets": bullets, "technologies": []},
                {"company": "E", "title": "T3", "start": "2016-01", "end": "2017-12",
                 "bullets": bullets, "technologies": []},
            ],
            "skills": ["Python"],
            "education": [{"institution": "U", "degree": "B"}],
        })

    def test_task_only_bullet_triggers_warning(self) -> None:
        """Very short task-only bullet without specificity triggers warning."""
        base = self._make_base(["test"])
        tailored = self._make_tailored(["Managed servers"])
        warnings = validate_tailored_cv(base, tailored)
        generic_warnings = [w for w in warnings if "Generic" in w or "generic" in w
                           or "task-only" in w]
        assert len(generic_warnings) > 0

    def test_detailed_bullet_no_generic_warning(self) -> None:
        """Detailed bullets with scale do not trigger generic warnings."""
        base = self._make_base(["test"])
        tailored = self._make_tailored([
            "Managed 50+ Kubernetes clusters across 3 regions with 99.9% uptime",
            "Designed CI/CD framework adopted by 4 teams, reducing deploy time 70%",
            "Led migration of 12 microservices to AWS EKS with zero downtime",
            "Mentored 3 junior engineers, reducing onboarding from 6 to 3 weeks",
            "Built internal developer platform serving 20+ engineering teams",
        ])
        warnings = validate_tailored_cv(base, tailored)
        generic_warnings = [w for w in warnings if "Generic" in w or "task-only" in w]
        assert len(generic_warnings) == 0

    def test_worked_on_phrase_triggers_warning(self) -> None:
        """'worked on' phrase triggers generic phrasing warning."""
        base = self._make_base(["test"])
        tailored = self._make_tailored([
            "Worked on CI/CD pipelines",
            "Built monitoring dashboards",
        ])
        warnings = validate_tailored_cv(base, tailored)
        phrase_warnings = [w for w in warnings if "Generic phrase" in w]
        assert len(phrase_warnings) > 0

    def test_active_verb_no_phrase_warning(self) -> None:
        """Active verb like 'Build' does not trigger generic phrase warning."""
        base = self._make_base(["test"])
        tailored = self._make_tailored([
            "Built CI/CD pipelines with GitHub Actions",
        ])
        warnings = validate_tailored_cv(base, tailored)
        phrase_warnings = [w for w in warnings if "Generic phrase" in w]
        assert len(phrase_warnings) == 0

    def test_generic_devops_pattern_triggers_warning(self) -> None:
        """Classic 'Managed X with Y' pattern triggers warning."""
        base = self._make_base(["test"])
        tailored = self._make_tailored([
            "Managed servers with Ansible",
        ])
        warnings = validate_tailored_cv(base, tailored)
        pattern_warnings = [w for w in warnings if "generic pattern" in w.lower()]
        assert len(pattern_warnings) > 0

    def test_bolded_generic_pattern_triggers_warning(self) -> None:
        """Bold-markdown generic bullet still triggers pattern warning."""
        base = self._make_base(["test"])
        tailored = self._make_tailored([
            "Managed **Kubernetes** deployments for production systems",
        ])
        warnings = validate_tailored_cv(base, tailored)
        pattern_warnings = [w for w in warnings if "generic pattern" in w.lower()]
        assert len(pattern_warnings) > 0

    def test_specific_bullet_avoids_pattern_warning(self) -> None:
        """Specific bullets avoid generic pattern warnings."""
        base = self._make_base(["test"])
        tailored = self._make_tailored([
            "Managed 200+ EC2 instances with Terraform, cutting provisioning time from days to hours",
        ])
        warnings = validate_tailored_cv(base, tailored)
        pattern_warnings = [w for w in warnings if "generic pattern" in w.lower()]
        assert len(pattern_warnings) == 0

    def test_low_ownership_density_warns(self) -> None:
        """CV with 5+ bullets but < 20% ownership signals triggers warning."""
        base = self._make_base(["test"] * 3)
        tailored = self._make_tailored([
            "Built REST APIs with Python",
            "Maintained internal tools",
            "Configured servers",
            "Wrote documentation",
            "Reviewed pull requests",
        ])
        warnings = validate_tailored_cv(base, tailored)
        density_warnings = [w for w in warnings if "ownership signal" in w.lower()]
        assert len(density_warnings) > 0

    def test_sufficient_ownership_no_density_warning(self) -> None:
        """CV with enough ownership signals avoids density warning."""
        base = self._make_base(["test"] * 3)
        tailored = self._make_tailored([
            "Led migration of 12 services to Kubernetes",
            "Reduced AWS costs by 30% through right-sizing",
            "Mentored junior engineers",
            "Standardized deploy processes across teams",
            "Automated incident response workflows",
        ])
        warnings = validate_tailored_cv(base, tailored)
        density_warnings = [w for w in warnings if "ownership signal" in w.lower()]
        assert len(density_warnings) == 0

    def test_case_insensitive_generic_phrase(self) -> None:
        """Case-insensitive matching for generic phrases."""
        base = self._make_base(["test"])
        tailored = self._make_tailored([
            "RESPONSIBLE FOR infrastructure maintenance",
        ])
        warnings = validate_tailored_cv(base, tailored)
        phrase_warnings = [w for w in warnings if "Generic phrase" in w]
        assert len(phrase_warnings) > 0

    def test_word_boundary_prevents_false_match(self) -> None:
        """'networked on' should not match 'worked on' pattern."""
        base = self._make_base(["test"])
        tailored = self._make_tailored([
            "Networked on-premise clusters with cloud VPCs",
        ])
        warnings = validate_tailored_cv(base, tailored)
        phrase_warnings = [w for w in warnings
                          if "worked on" in w.lower() and "networked" not in w.lower()]
        assert len(phrase_warnings) == 0

    def test_generic_warnings_coexist_with_other_warnings(self) -> None:
        """Generic, keyword, and metric warnings all appear together."""
        base = BaseCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [
                {"company": "C", "title": "T", "start": "2020-01",
                 "bullets": ["test"], "technologies": []},
                {"company": "D", "title": "T2", "start": "2018-01", "end": "2019-12",
                 "bullets": ["test"], "technologies": []},
            ],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        tailored = TailoredCV.model_validate({
            "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
            "summary": "Test.",
            "experience": [
                {"company": "C", "title": "T", "start": "2020-01",
                 "bullets": [
                     "Worked on Kubernetes, Terraform, AWS, CI/CD for 50+ services with 99.9% uptime",
                 ], "technologies": []},
                {"company": "D", "title": "T2", "start": "2018-01", "end": "2019-12",
                 "bullets": [
                     "Managed Kubernetes clusters",
                     "Deployed Terraform modules",
                     "Configured AWS IAM",
                     "Set up CI/CD pipelines",
                     "Built monitoring dashboards",
                 ], "technologies": []},
            ],
            "skills": ["Python", "Kubernetes", "Terraform"],
            "education": [{"institution": "U", "degree": "B"}],
        })
        warnings = validate_tailored_cv(
            base, tailored,
            jd_keywords=["Kubernetes", "Terraform", "AWS", "CI/CD"],
        )
        generic_warnings = [w for w in warnings
                           if "Generic" in w or "generic" in w]
        kw_warnings = [w for w in warnings if "keyword" in w.lower()]
        metric_warnings = [w for w in warnings if "metric" in w.lower()]
        assert len(generic_warnings) > 0
        assert len(kw_warnings) > 0
        assert len(metric_warnings) > 0
