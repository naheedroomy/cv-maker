"""Tests for cv_maker.pipeline — all subprocess calls monkeypatched."""
from __future__ import annotations

import json
import subprocess
import types

import pytest

import cv_maker.pipeline as pipeline
from cv_maker.models import BaseCV, GapItem, TailoredCV
from cv_maker.pipeline import _build_prompt, run_pipeline

# ---------------------------------------------------------------------------
# Module-level JSON fixtures — minimal valid payloads matching each schema
# ---------------------------------------------------------------------------

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
    "gap_diff": [
        {"requirement": "Python", "match_level": "strong", "evidence": "8 years Python"},
        {"requirement": "Kubernetes", "match_level": "missing", "evidence": ""},
    ],
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
# _build_prompt — unit tests
# ---------------------------------------------------------------------------


def test_build_prompt_contains_base_cv_yaml(base_cv: BaseCV, sample_job_text: str) -> None:
    """_build_prompt embeds the base CV name in the prompt."""
    prompt = _build_prompt(base_cv, sample_job_text)
    assert "Jane Smith" in prompt


def test_build_prompt_contains_job_text(base_cv: BaseCV, sample_job_text: str) -> None:
    """_build_prompt embeds the job listing text in the prompt."""
    prompt = _build_prompt(base_cv, sample_job_text)
    assert sample_job_text in prompt


def test_build_prompt_returns_string(base_cv: BaseCV, sample_job_text: str) -> None:
    """_build_prompt returns a non-empty string."""
    prompt = _build_prompt(base_cv, sample_job_text)
    assert isinstance(prompt, str)
    assert len(prompt) > 100  # noqa: PLR2004


# ---------------------------------------------------------------------------
# run_pipeline tests
# ---------------------------------------------------------------------------


def test_run_pipeline_happy_path(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Happy path: subprocess returns clean TailoredCV JSON, result is (TailoredCV, list[GapItem])."""
    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(
        lambda cmd, **kw: _make_proc(TAILORED_CV_JSON)
    ))
    result = run_pipeline(base_cv, sample_job_text)
    tailored, gap = result
    assert isinstance(tailored, TailoredCV)
    assert tailored.summary == "Python engineer with FastAPI expertise."
    assert "Redis" in tailored.highlighted_technologies
    assert isinstance(gap, list)
    assert all(isinstance(g, GapItem) for g in gap)


def test_run_pipeline_returns_tailored_cv_and_gap_diff(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """run_pipeline: single subprocess call returns (TailoredCV, list[GapItem])."""
    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(
        lambda cmd, **kw: _make_proc(TAILORED_CV_JSON)
    ))
    tailored, gap = run_pipeline(base_cv, sample_job_text)
    assert isinstance(tailored, TailoredCV)
    assert isinstance(gap, list)
    assert all(isinstance(g, GapItem) for g in gap)
    assert len(gap) == 2


def test_run_pipeline_handles_fenced_json(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Subprocess returns ```json...``` fenced output — still returns (TailoredCV, list[GapItem])."""
    fenced = f"```json\n{TAILORED_CV_JSON}\n```"
    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(
        lambda cmd, **kw: _make_proc(fenced)
    ))
    tailored, gap = run_pipeline(base_cv, sample_job_text)
    assert isinstance(tailored, TailoredCV)
    assert tailored.summary == "Python engineer with FastAPI expertise."


def test_run_pipeline_retries_on_bad_json(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Retry: subprocess returns invalid JSON on attempt 1, valid JSON on attempt 2."""
    call_count = []

    def fake_run(cmd, **kwargs):
        call_count.append(1)
        if len(call_count) == 1:
            return _make_proc("not valid json at all")
        return _make_proc(TAILORED_CV_JSON)

    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(fake_run))
    tailored, gap = run_pipeline(base_cv, sample_job_text)
    assert isinstance(tailored, TailoredCV)
    assert len(call_count) == 2  # failed once, succeeded on retry


def test_run_pipeline_exhausts_retries(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Exhausts retries: subprocess always returns garbage; RuntimeError with 3 attempts."""
    call_count = []

    def fake_run(cmd, **kwargs):
        call_count.append(1)
        return _make_proc("garbage output, no json here")

    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(fake_run))
    with pytest.raises(RuntimeError, match="3 attempts"):
        run_pipeline(base_cv, sample_job_text)
    assert len(call_count) == 3


def test_run_pipeline_raises_on_timeout(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Timeout: subprocess raises TimeoutExpired; RuntimeError with 'timed out'."""
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=120)

    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(fake_run))
    with pytest.raises(RuntimeError, match="timed out"):
        run_pipeline(base_cv, sample_job_text)


def test_run_pipeline_raises_on_nonzero_exit(
    monkeypatch, base_cv: BaseCV, sample_job_text: str
) -> None:
    """Non-zero exit code: RuntimeError with exit code in message."""
    monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(
        lambda cmd, **kw: _make_proc("", returncode=1)
    ))
    with pytest.raises(RuntimeError, match="exit 1"):
        run_pipeline(base_cv, sample_job_text)
