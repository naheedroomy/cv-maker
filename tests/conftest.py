# tests/conftest.py
from pathlib import Path

import pytest

from core.models import (
    BaseCV,
    EvidenceMap,
    EvidenceMatch,
    JDRequirement,
    KeywordPair,
    KeywordPairingPlan,
    RequirementExtraction,
    TailoredCV,
)

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
    """Path to the canonical base_cv.yaml in the data/ directory."""
    return Path("data/base_cv.yaml")


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


@pytest.fixture
def jd_with_keywords() -> str:
    """JD with 8-12 explicit keyword phrases for keyword-stuffing validation tests."""
    return (
        "Senior Platform Engineer — Cloud Infrastructure\n\n"
        "We are looking for a Senior Platform Engineer to design, build, and maintain "
        "our cloud-native infrastructure. The ideal candidate has:\n\n"
        "Required:\n"
        "- 5+ years experience with Kubernetes and container orchestration\n"
        "- Strong expertise in Terraform for infrastructure as code\n"
        "- Deep knowledge of AWS services (EC2, S3, RDS, Lambda)\n"
        "- Experience building and maintaining CI/CD pipelines (GitHub Actions, Jenkins)\n"
        "- Proficiency in Python for automation and tooling\n"
        "- Experience with monitoring and observability (Datadog, Prometheus, Grafana)\n"
        "- Strong understanding of networking (VPC, DNS, load balancers)\n\n"
        "Nice to have:\n"
        "- Experience with service mesh (Istio, Linkerd)\n"
        "- Familiarity with GitOps workflows (ArgoCD, Flux)\n"
        "- Knowledge of security best practices (IAM, secrets management)\n"
        "- Experience with Go or Rust for systems programming"
    )


@pytest.fixture
def jd_keywords_list() -> list[str]:
    """Keyword phrases from the jd_with_keywords fixture."""
    return [
        "Kubernetes", "container orchestration", "Terraform", "infrastructure as code",
        "AWS", "EC2", "S3", "RDS", "Lambda", "CI/CD", "GitHub Actions", "Jenkins",
        "Python", "monitoring", "Datadog", "Prometheus", "Grafana",
        "networking", "VPC", "DNS", "load balancers",
        "service mesh", "Istio", "GitOps", "ArgoCD", "security", "IAM", "Go",
    ]


@pytest.fixture
def base_cv_partial_evidence() -> BaseCV:
    """Base CV with ~60% evidence for jd_with_keywords, ~20% partial, ~20% missing."""
    return BaseCV.model_validate({
        "contact": {"name": "Alex Chen", "email": "alex@example.com", "github": "github.com/alex"},
        "summary": "Platform engineer with 6 years in cloud infrastructure and DevOps.",
        "experience": [
            {
                "company": "CloudCo",
                "title": "Platform Engineer",
                "start": "2020-06",
                "end": "2024-03",
                "bullets": [
                    "Managed 50+ Kubernetes clusters across 3 AWS regions using Terraform",
                    "Built CI/CD pipelines with GitHub Actions, reducing deploy time by 70%",
                    "Implemented Datadog monitoring and Prometheus alerting for 200+ services",
                    "Automated infrastructure provisioning with Python and Terraform",
                ],
                "technologies": [
                    "Kubernetes", "Terraform", "AWS", "GitHub Actions",
                    "Datadog", "Prometheus", "Python",
                ],
            },
            {
                "company": "StartupInc",
                "title": "DevOps Engineer",
                "start": "2018-01",
                "end": "2020-05",
                "bullets": [
                    "Maintained Jenkins pipelines for 10+ microservices",
                    "Configured VPC networking and load balancers on AWS",
                ],
                "technologies": ["Jenkins", "AWS", "Docker"],
            },
        ],
        "skills": [
            "Kubernetes", "Terraform", "AWS", "Python", "GitHub Actions",
            "Jenkins", "Docker", "Datadog", "Prometheus", "Linux",
        ],
        "education": [
            {"institution": "Tech University", "degree": "BSc", "field": "Computer Science", "year": 2017},
        ],
    })


@pytest.fixture
def expected_requirements() -> RequirementExtraction:
    """Golden expected requirement extraction for jd_with_keywords (partial)."""
    return RequirementExtraction.model_validate({
        "requirements": [
            {"phrase": "Kubernetes", "category": "technology", "tier": 1,
             "related_phrases": ["container orchestration"], "description": "5+ years experience with Kubernetes"},
            {"phrase": "Terraform", "category": "technology", "tier": 1,
             "related_phrases": ["infrastructure as code"], "description": "Strong expertise in Terraform"},
            {"phrase": "AWS", "category": "technology", "tier": 1,
             "related_phrases": ["EC2", "S3", "RDS", "Lambda"], "description": "Deep knowledge of AWS services"},
            {"phrase": "CI/CD", "category": "methodology", "tier": 2,
             "related_phrases": ["GitHub Actions", "Jenkins"], "description": "Experience building CI/CD pipelines"},
            {"phrase": "Python", "category": "technology", "tier": 1,
             "related_phrases": ["automation", "tooling"], "description": "Proficiency in Python"},
            {"phrase": "Monitoring", "category": "domain", "tier": 2,
             "related_phrases": ["Datadog", "Prometheus", "Grafana"], "description": "Experience with monitoring and observability"},
            {"phrase": "Networking", "category": "domain", "tier": 2,
             "related_phrases": ["VPC", "DNS", "load balancers"], "description": "Strong understanding of networking"},
            {"phrase": "Service Mesh", "category": "technology", "tier": 3,
             "related_phrases": ["Istio", "Linkerd"], "description": "Experience with service mesh"},
            {"phrase": "GitOps", "category": "methodology", "tier": 3,
             "related_phrases": ["ArgoCD", "Flux"], "description": "Familiarity with GitOps workflows"},
            {"phrase": "Security", "category": "domain", "tier": 3,
             "related_phrases": ["IAM", "secrets management"], "description": "Knowledge of security best practices"},
        ],
        "raw_jd_hash": "placeholder",
    })


@pytest.fixture
def expected_evidence_map() -> EvidenceMap:
    """Golden expected evidence map matching jd_with_keywords to base_cv_partial_evidence."""
    return EvidenceMap.model_validate({
        "matches": [
            {"requirement_phrase": "Kubernetes", "match_level": "strong",
             "source_company": "CloudCo", "source_role": "Platform Engineer", "source_bullet_index": 0,
             "source_field": "experience.bullets[0]", "evidence_text": "Managed 50+ Kubernetes clusters",
             "allowed_keywords": ["Kubernetes"], "inference_rule": None},
            {"requirement_phrase": "Terraform", "match_level": "strong",
             "source_company": "CloudCo", "source_role": "Platform Engineer", "source_bullet_index": 0,
             "source_field": "experience.bullets[0]", "evidence_text": "Managed ... clusters using Terraform",
             "allowed_keywords": ["Terraform", "infrastructure as code"], "inference_rule": None},
            {"requirement_phrase": "AWS", "match_level": "strong",
             "source_company": "CloudCo", "source_role": "Platform Engineer", "source_bullet_index": 0,
             "source_field": "experience.bullets[0]", "evidence_text": "across 3 AWS regions",
             "allowed_keywords": ["AWS", "EC2"], "inference_rule": None},
            {"requirement_phrase": "CI/CD", "match_level": "strong",
             "source_company": "CloudCo", "source_role": "Platform Engineer", "source_bullet_index": 1,
             "source_field": "experience.bullets[1]", "evidence_text": "Built CI/CD pipelines with GitHub Actions",
             "allowed_keywords": ["CI/CD", "GitHub Actions"], "inference_rule": None},
            {"requirement_phrase": "Python", "match_level": "strong",
             "source_company": "CloudCo", "source_role": "Platform Engineer", "source_bullet_index": 3,
             "source_field": "experience.bullets[3]", "evidence_text": "Automated infrastructure provisioning with Python",
             "allowed_keywords": ["Python"], "inference_rule": None},
            {"requirement_phrase": "Monitoring", "match_level": "strong",
             "source_company": "CloudCo", "source_role": "Platform Engineer", "source_bullet_index": 2,
             "source_field": "experience.bullets[2]", "evidence_text": "Implemented Datadog monitoring and Prometheus alerting",
             "allowed_keywords": ["Monitoring", "Datadog", "Prometheus"], "inference_rule": None},
            {"requirement_phrase": "Networking", "match_level": "strong",
             "source_company": "StartupInc", "source_role": "DevOps Engineer", "source_bullet_index": 1,
             "source_field": "experience.bullets[1]", "evidence_text": "Configured VPC networking and load balancers",
             "allowed_keywords": ["Networking", "VPC", "load balancers"], "inference_rule": None},
            {"requirement_phrase": "Service Mesh", "match_level": "partial",
             "source_company": "CloudCo", "source_role": "Platform Engineer", "source_bullet_index": 0,
             "source_field": None, "evidence_text": "Kubernetes experience implies service mesh awareness",
             "allowed_keywords": ["Service Mesh", "Istio"], "inference_rule": "technology_adjacency"},
            {"requirement_phrase": "GitOps", "match_level": "missing",
             "source_company": None, "source_role": None, "source_bullet_index": None,
             "source_field": None, "evidence_text": "",
             "allowed_keywords": [], "inference_rule": None},
            {"requirement_phrase": "Security", "match_level": "partial",
             "source_company": "CloudCo", "source_role": "Platform Engineer", "source_bullet_index": None,
             "source_field": None, "evidence_text": "AWS infrastructure work implies IAM and security knowledge",
             "allowed_keywords": ["Security", "IAM"], "inference_rule": "domain_adjacency"},
        ],
        "pairing_plan": {
            "pairs": [
                {"keywords": ["Kubernetes", "Terraform"], "rationale": "Both used together for cluster management",
                 "evidence_source": "CloudCo/Platform Engineer", "suggested_bullet_count": 1},
                {"keywords": ["CI/CD", "GitHub Actions"], "rationale": "CI/CD implemented with GitHub Actions",
                 "evidence_source": "CloudCo/Platform Engineer", "suggested_bullet_count": 1},
                {"keywords": ["Monitoring", "Datadog", "Prometheus"], "rationale": "Observability stack used together",
                 "evidence_source": "CloudCo/Platform Engineer", "suggested_bullet_count": 1},
            ],
        },
        "coverage_summary": {"total_requirements": 10, "strong_matches": 7, "partial_matches": 2, "missing": 1},
    })
