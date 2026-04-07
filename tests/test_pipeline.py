"""Tests for cv_maker.pipeline — all subprocess calls monkeypatched."""
from __future__ import annotations

import json
import subprocess
import types

import pytest

import cv_maker.pipeline as pipeline
from cv_maker.models import BaseCV, GapItem, TailoredCV
from cv_maker.pipeline import Creativity, _build_prompt, _resolve_rule, run_pipeline

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
# Parameterized prompt — _resolve_rule tests
# ---------------------------------------------------------------------------


class TestResolveRule:
    """Tests for _resolve_rule — picks the right instruction per creativity level."""

    def test_exact_match(self) -> None:
        """Exact level key returns that level's instruction."""
        result = _resolve_rule("titles", 0)
        assert "Do NOT change any job titles" in result

    def test_inherits_from_lower_level(self) -> None:
        """If no key for requested level, inherits from highest key below it."""
        # Inference only defines 0, 1, 2 — level 4 should inherit from 2
        result = _resolve_rule("inference", 4)
        assert "Technology adjacency" in result

    def test_all_rules_have_level_2(self) -> None:
        """Every rule concern has a level 2 definition (the default)."""
        for rule_name in pipeline._RULES:
            result = _resolve_rule(rule_name, 2)
            assert isinstance(result, str)
            assert len(result) > 0


class TestParameterizedPrompt:
    """Tests for the parameterized prompt builder."""

    def test_level_0_contains_strict_title_rule(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 0 prompt includes 'Do NOT change any job titles'."""
        result = _build_prompt(base_cv, sample_job_text, 0)
        assert "Do NOT change any job titles" in result

    def test_level_0_contains_strict_bullet_rule(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 0 prompt includes 'Only REORDER existing bullets'."""
        result = _build_prompt(base_cv, sample_job_text, 0)
        assert "Only REORDER existing bullets" in result

    def test_level_2_contains_inference_rules(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 2 prompt includes inference rules (technology adjacency etc.)."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "Technology adjacency" in result
        assert "Infrastructure fundamentals" in result

    def test_level_4_contains_exposure_language(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 4 prompt includes 'exposure, not ownership' language."""
        result = _build_prompt(base_cv, sample_job_text, 4)
        assert "exposure" in result.lower()

    def test_level_5_contains_fabrication_warning(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 5 prompt includes fabrication warning."""
        result = _build_prompt(base_cv, sample_job_text, 5)
        assert "fabricate" in result.lower()
        assert "WARNING" in result

    def test_level_label_embedded(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes the level number and name."""
        result = _build_prompt(base_cv, sample_job_text, 3)
        assert "CREATIVITY LEVEL: 3 (FORWARD)" in result

    def test_all_levels_produce_distinct_prompts(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """All 6 levels produce distinct prompt text."""
        prompts = [_build_prompt(base_cv, sample_job_text, i) for i in range(6)]
        assert len(set(prompts)) == 6

    def test_default_is_level_2(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Calling without creativity_level defaults to level 2."""
        default = _build_prompt(base_cv, sample_job_text)
        explicit = _build_prompt(base_cv, sample_job_text, 2)
        assert default == explicit

    def test_no_split_rule_present(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes the no-split rule for role structure."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "Do NOT split a single role" in result

    def test_signal_density_present(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes signal density guidance."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "Signal density" in result

    def test_coverage_constraint_present(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes minimum bullet count constraint."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "FLOORS" in result or "minimum" in result.lower()

    def test_level_clamped_to_range(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Levels outside 0-5 are clamped."""
        low = _build_prompt(base_cv, sample_job_text, -1)
        zero = _build_prompt(base_cv, sample_job_text, 0)
        assert low == zero
        high = _build_prompt(base_cv, sample_job_text, 99)
        five = _build_prompt(base_cv, sample_job_text, 5)
        assert high == five


class TestChatPrompt:
    """Tests for _build_system_prompt_for_chat."""

    def test_includes_cot_preamble(self) -> None:
        """Chat prompt includes chain-of-thought steps."""
        result = pipeline._build_system_prompt_for_chat(2)
        assert "Step 1:" in result
        assert "Step 5:" in result

    def test_level_0_includes_restrictions(self) -> None:
        """Level 0 chat prompt includes title restrictions."""
        result = pipeline._build_system_prompt_for_chat(0)
        assert "Do NOT change any job titles" in result

    def test_level_embedded(self) -> None:
        """Chat prompt includes level label."""
        result = pipeline._build_system_prompt_for_chat(3)
        assert "CREATIVITY LEVEL: 3 (FORWARD)" in result


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


class TestCreativityEnum:
    """Tests for the Creativity IntEnum."""

    def test_values(self) -> None:
        assert Creativity.STRICT == 0
        assert Creativity.DEFAULT == 2
        assert Creativity.CREATIVE == 5

    def test_name_lookup(self) -> None:
        assert Creativity(3).name == "FORWARD"
        assert Creativity(4).name == "BOLD"
