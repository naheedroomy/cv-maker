"""Tests for cv_maker.pipeline — all subprocess calls monkeypatched."""
from __future__ import annotations

import json
import subprocess
import types

import pytest

import cv_maker.pipeline as pipeline
from cv_maker.models import BaseCV, GapItem, JobAnalysis, TailoredCV
from cv_maker.pipeline import analyze_job, run_pipeline, tailor_cv

# ---------------------------------------------------------------------------
# Module-level JSON fixtures — minimal valid payloads matching each schema
# ---------------------------------------------------------------------------

JOB_ANALYSIS_JSON = json.dumps({
    "role_title": "Senior Backend Engineer",
    "key_requirements": ["Python", "REST API design"],
    "required_technologies": ["Python", "FastAPI", "PostgreSQL"],
    "gap_diff": [
        {"requirement": "Python", "present": True, "evidence": "8 years Python"},
        {"requirement": "Kubernetes", "present": False, "evidence": ""},
    ],
})

TAILORED_CV_JSON = json.dumps({
    "contact": {"name": "Jane Smith", "email": "jane@example.com"},
    "summary": "Python engineer with FastAPI expertise.",
    "experience": [
        {
            "company": "TechCorp",
            "title": "Senior Software Engineer",
            "start": "2019-03",
            "end": "2024-01",
            "bullets": ["Built REST APIs using Python and FastAPI"],
            "technologies": ["Python", "FastAPI"],
        }
    ],
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "education": [{"institution": "State University", "degree": "BSc"}],
    "highlighted_technologies": ["Redis", "Docker"],
})


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_proc(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["claude", "-p", "--no-session-persistence", "..."],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


def _mock_subprocess(fake_run) -> types.SimpleNamespace:
    """Build a mock subprocess module with a given run function."""
    return types.SimpleNamespace(
        run=fake_run,
        TimeoutExpired=subprocess.TimeoutExpired,
    )


# ---------------------------------------------------------------------------
# _extract_json — direct tests, no monkeypatching needed
# ---------------------------------------------------------------------------


def test_extract_json_parses_clean_json() -> None:
    """Clean JSON string is parsed directly without fence-stripping."""
    data = pipeline._extract_json('{"key": "value"}')
    assert data == {"key": "value"}


def test_extract_json_strips_json_fence() -> None:
    """Output wrapped in ```json...``` fences is correctly extracted."""
    fenced = '```json\n{"key": "value"}\n```'
    data = pipeline._extract_json(fenced)
    assert data == {"key": "value"}


def test_extract_json_strips_plain_fence() -> None:
    """Output wrapped in plain ``` fences (no language tag) is extracted."""
    fenced = '```\n{"key": "value"}\n```'
    data = pipeline._extract_json(fenced)
    assert data == {"key": "value"}


def test_extract_json_raises_on_no_json() -> None:
    """ValueError raised when no JSON object is present in the output."""
    with pytest.raises(ValueError, match="No JSON object found"):
        pipeline._extract_json("just plain text with no json")


# ---------------------------------------------------------------------------
# analyze_job tests
# ---------------------------------------------------------------------------


def test_analyze_job_happy_path(monkeypatch, base_cv: BaseCV, sample_job_text: str) -> None:
    """Happy path: subprocess returns clean JobAnalysis JSON, result is JobAnalysis."""
    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(
        lambda cmd, **kw: _make_proc(JOB_ANALYSIS_JSON)
    ))
    result = analyze_job(base_cv, sample_job_text)
    assert isinstance(result, JobAnalysis)
    assert result.role_title == "Senior Backend Engineer"
    assert "Python" in result.required_technologies


def test_analyze_job_handles_fenced_json(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Subprocess returns ```json...``` fenced output — still returns JobAnalysis."""
    fenced = f"```json\n{JOB_ANALYSIS_JSON}\n```"
    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(
        lambda cmd, **kw: _make_proc(fenced)
    ))
    result = analyze_job(base_cv, sample_job_text)
    assert isinstance(result, JobAnalysis)
    assert result.role_title == "Senior Backend Engineer"


def test_analyze_job_retries_on_bad_json(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Retry: subprocess returns invalid JSON on attempt 1, valid JSON on attempt 2."""
    call_count = []

    def fake_run(cmd, **kwargs):
        call_count.append(1)
        if len(call_count) == 1:
            return _make_proc("not valid json at all")
        return _make_proc(JOB_ANALYSIS_JSON)

    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(fake_run))
    result = analyze_job(base_cv, sample_job_text)
    assert isinstance(result, JobAnalysis)
    assert len(call_count) == 2  # failed once, succeeded on retry


def test_analyze_job_exhausts_retries(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Exhausts retries: subprocess always returns garbage; RuntimeError with 3 attempts."""
    call_count = []

    def fake_run(cmd, **kwargs):
        call_count.append(1)
        return _make_proc("garbage output, no json here")

    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(fake_run))
    with pytest.raises(RuntimeError, match="3 attempts"):
        analyze_job(base_cv, sample_job_text)
    assert len(call_count) == 3


def test_analyze_job_raises_on_timeout(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Timeout: subprocess raises TimeoutExpired; RuntimeError with 'timed out'."""
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=120)

    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(fake_run))
    with pytest.raises(RuntimeError, match="timed out"):
        analyze_job(base_cv, sample_job_text)


def test_analyze_job_raises_on_nonzero_exit(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Non-zero exit code: RuntimeError with exit code in message."""
    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(
        lambda cmd, **kw: _make_proc("", returncode=1)
    ))
    with pytest.raises(RuntimeError, match="exit 1"):
        analyze_job(base_cv, sample_job_text)


# ---------------------------------------------------------------------------
# tailor_cv tests
# ---------------------------------------------------------------------------


def test_tailor_cv_happy_path(monkeypatch, base_cv: BaseCV, sample_job_text: str) -> None:
    """Happy path: subprocess returns clean TailoredCV JSON, result is TailoredCV."""
    analysis = JobAnalysis.model_validate(json.loads(JOB_ANALYSIS_JSON))
    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(
        lambda cmd, **kw: _make_proc(TAILORED_CV_JSON)
    ))
    result = tailor_cv(base_cv, analysis)
    assert isinstance(result, TailoredCV)
    assert result.summary == "Python engineer with FastAPI expertise."
    assert "Redis" in result.highlighted_technologies


# ---------------------------------------------------------------------------
# run_pipeline tests
# ---------------------------------------------------------------------------


def test_run_pipeline_returns_tailored_cv_and_gap_diff(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """run_pipeline: two sequential subprocess calls return (TailoredCV, list[GapItem])."""
    responses = [JOB_ANALYSIS_JSON, TAILORED_CV_JSON]
    call_idx = [0]

    def fake_run(cmd, **kwargs):
        resp = responses[call_idx[0]]
        call_idx[0] += 1
        return _make_proc(resp)

    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(fake_run))
    tailored, gap = run_pipeline(base_cv, sample_job_text)
    assert isinstance(tailored, TailoredCV)
    assert isinstance(gap, list)
    assert all(isinstance(g, GapItem) for g in gap)
    assert len(gap) == 2
