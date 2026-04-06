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


# ---------------------------------------------------------------------------
# Creativity level tests
# ---------------------------------------------------------------------------

# Capture baseline prompt ONCE at module import (before any tests modify it).
# This is the "golden" reference for backward compatibility.
_BASELINE_SYSTEM_PROMPT = pipeline._build_system_prompt()
_BASELINE_PROMPT_FOR_CHAT = pipeline._build_system_prompt_for_chat()


class TestBuildCreativityInstructions:
    """Tests for the _build_creativity_instructions helper."""

    def test_level_2_returns_empty_string(self) -> None:
        """Level 2 (default) returns empty string — no modifications to prompt."""
        result = pipeline._build_creativity_instructions(2)
        assert result == ""

    def test_level_0_contains_strict_constraints(self) -> None:
        """Level 0 (Strict) includes restrictive 'Do NOT' instructions."""
        result = pipeline._build_creativity_instructions(0)
        assert "Do NOT change any job titles" in result
        assert "Do NOT add new bullet points" in result

    def test_level_1_contains_conservative_constraints(self) -> None:
        """Level 1 (Conservative) includes moderate restrictions."""
        result = pipeline._build_creativity_instructions(1)
        assert "Do NOT adjust job titles" in result

    def test_level_3_contains_forward_permissions(self) -> None:
        """Level 3 (Forward) focuses on addressing gaps."""
        result = pipeline._build_creativity_instructions(3)
        assert "ADDRESSING GAPS" in result

    def test_level_4_contains_bold_permissions(self) -> None:
        """Level 4 (Bold) includes fill-gap language."""
        result = pipeline._build_creativity_instructions(4)
        assert "fill gaps" in result.lower()

    def test_level_5_contains_creative_permissions(self) -> None:
        """Level 5 (Creative) includes fabrication language."""
        result = pipeline._build_creativity_instructions(5)
        assert "fabricate" in result.lower()

    def test_all_levels_return_distinct_text(self) -> None:
        """All six levels produce distinct instruction text."""
        results = [pipeline._build_creativity_instructions(i) for i in range(6)]
        assert len(set(results)) == 6, f"Expected 6 distinct results, got {len(set(results))}"


class TestBuildSystemPromptCreativity:
    """Tests for _build_system_prompt with creativity_level parameter."""

    def test_level_2_identical_to_baseline(self) -> None:
        """Level 2 produces byte-for-byte identical output to baseline (backward compat)."""
        result = pipeline._build_system_prompt(2)
        assert result == _BASELINE_SYSTEM_PROMPT

    def test_default_identical_to_baseline(self) -> None:
        """Calling with no argument produces same output as baseline."""
        result = pipeline._build_system_prompt()
        assert result == _BASELINE_SYSTEM_PROMPT

    def test_level_0_prepends_restrictions(self) -> None:
        """Level 0 instructions appear BEFORE the existing prompt content."""
        result = pipeline._build_system_prompt(0)
        strict_pos = result.find("CREATIVITY LEVEL: 0")
        expert_pos = result.find("You are a CV tailoring expert")
        assert strict_pos < expert_pos, "Level 0 instructions should be prepended"

    def test_level_1_prepends_restrictions(self) -> None:
        """Level 1 instructions appear BEFORE the existing prompt content."""
        result = pipeline._build_system_prompt(1)
        conservative_pos = result.find("CREATIVITY LEVEL: 1")
        expert_pos = result.find("You are a CV tailoring expert")
        assert conservative_pos < expert_pos, "Level 1 instructions should be prepended"

    def test_level_3_appends_permissions(self) -> None:
        """Level 3 instructions appear AFTER the existing prompt content."""
        result = pipeline._build_system_prompt(3)
        # The existing prompt's last major content
        schema_pos = result.rfind("gap_diff")
        forward_pos = result.find("CREATIVITY LEVEL: 3")
        assert forward_pos > schema_pos, "Level 3 instructions should be appended"

    def test_level_5_appends_permissions(self) -> None:
        """Level 5 instructions appear AFTER the existing prompt content."""
        result = pipeline._build_system_prompt(5)
        schema_pos = result.rfind("gap_diff")
        creative_pos = result.find("CREATIVITY LEVEL: 5")
        assert creative_pos > schema_pos, "Level 5 instructions should be appended"


class TestBuildSystemPromptForChatCreativity:
    """Tests for _build_system_prompt_for_chat with creativity_level parameter."""

    def test_level_2_identical_to_baseline(self) -> None:
        """Level 2 for chat produces identical output to baseline."""
        result = pipeline._build_system_prompt_for_chat(2)
        assert result == _BASELINE_PROMPT_FOR_CHAT

    def test_level_0_includes_restrictions(self) -> None:
        """Level 0 for chat includes 'Do NOT change any job titles'."""
        result = pipeline._build_system_prompt_for_chat(0)
        assert "Do NOT change any job titles" in result


class TestBuildPromptCreativity:
    """Tests for _build_prompt with creativity_level."""

    def test_level_0_includes_restrictions(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """_build_prompt with level 0 includes level 0 restrictions."""
        result = pipeline._build_prompt(base_cv, sample_job_text, 0)
        assert "Do NOT change any job titles" in result

    def test_level_2_matches_baseline(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """_build_prompt with level 2 matches current behavior."""
        baseline = pipeline._build_prompt(base_cv, sample_job_text)
        result = pipeline._build_prompt(base_cv, sample_job_text, 2)
        assert result == baseline


class TestRunPipelineCreativity:
    """Tests for run_pipeline with creativity_level parameter."""

    def test_level_3_passes_through_to_prompt(
        self, monkeypatch, base_cv: BaseCV, sample_job_text: str
    ) -> None:
        """run_pipeline(level=3) passes level through to prompt — prompt contains level 3 text."""
        captured_prompts = []

        def fake_run(cmd, **kwargs):
            captured_prompts.append(kwargs.get("input", ""))
            return _make_proc(TAILORED_CV_JSON)

        monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(fake_run))
        run_pipeline(base_cv, sample_job_text, 3)
        assert len(captured_prompts) == 1
        assert "CREATIVITY LEVEL: 3" in captured_prompts[0]
