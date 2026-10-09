"""Tests for cv_maker.pipeline — all subprocess calls monkeypatched."""
from __future__ import annotations

import json
import subprocess
import types

import pytest

import core.pipeline as pipeline
from core.models import BaseCV, GapItem, TailoredCV
from core.pipeline import (
    Creativity,
    _build_prompt,
    _build_system_prompt_for_chat,
    _build_user_prompt,
    _resolve_rule,
    run_pipeline,
)

# ---------------------------------------------------------------------------
# Module-level JSON fixtures — minimal valid payloads matching each schema
# ---------------------------------------------------------------------------

TAILORED_CV_JSON = json.dumps({
    "contact": {"name": "Jane Smith", "email": "jane@example.com", "github": "github.com/jane"},
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
        # Inference only defines 0, 1, 2 — level 3 should inherit from 2
        result = _resolve_rule("inference", 3)
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

    def test_level_3_contains_limited_substitution(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 3 prompt includes limited substitution (one role only) without soft-fabrication."""
        result = _build_prompt(base_cv, sample_job_text, 3)
        assert "LIMITED STACK SUBSTITUTION" in result
        assert "AT MOST 1 role" in result
        assert "No new bullets" in result
        assert "Prefer the second most recent role" in result
        assert "Do NOT substitute technologies in the most recent/current role" in result

    def test_level_label_embedded(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes the level number and name."""
        result = _build_prompt(base_cv, sample_job_text, 3)
        assert "CREATIVITY LEVEL: 3 (SELECTIVE)" in result

    def test_all_levels_produce_distinct_prompts(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """All 4 levels produce distinct prompt text."""
        prompts = [_build_prompt(base_cv, sample_job_text, i) for i in range(4)]
        assert len(set(prompts)) == 4

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

    def test_english_only_sanity_check_present(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt requires final CV output to stay in English."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "LANGUAGE SANITY CHECK" in result
        assert "entirely in English" in result
        assert "Do not copy non-English wording" in result

    def test_coverage_constraint_present(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes minimum bullet count constraint."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "FLOORS" in result or "minimum" in result.lower()

    def test_level_clamped_to_range(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Levels outside 0-3 are clamped."""
        low = _build_prompt(base_cv, sample_job_text, -1)
        zero = _build_prompt(base_cv, sample_job_text, 0)
        assert low == zero
        high = _build_prompt(base_cv, sample_job_text, 99)
        three = _build_prompt(base_cv, sample_job_text, 3)
        assert high == three


class TestChatPrompt:
    """Tests for _build_system_prompt_for_chat."""

    @pytest.mark.parametrize("level", range(4))
    def test_cli_and_chat_share_rules(
        self, base_cv: BaseCV, sample_job_text: str, level: int
    ) -> None:
        instructions = pipeline._build_system_prompt_for_chat(level)
        user_data = pipeline._build_user_prompt(base_cv, sample_job_text)
        assert _build_prompt(base_cv, sample_job_text, level) == instructions + "\n\n" + user_data
        assert sample_job_text not in instructions
        assert "BASE CV:" not in instructions

    def test_includes_cot_preamble(self) -> None:
        """Chat prompt includes chain-of-thought steps."""
        result = pipeline._build_system_prompt_for_chat(2)
        assert "Step 1:" in result
        assert "STEP 3 — TAILORING NOTES" in result

    def test_level_0_includes_restrictions(self) -> None:
        """Level 0 chat prompt includes title restrictions."""
        result = pipeline._build_system_prompt_for_chat(0)
        assert "Do NOT change any job titles" in result

    def test_level_embedded(self) -> None:
        """Chat prompt includes level label."""
        result = pipeline._build_system_prompt_for_chat(3)
        assert "CREATIVITY LEVEL: 3 (SELECTIVE)" in result

    def test_english_only_sanity_check_present(self) -> None:
        """Chat prompt requires final CV output to stay in English."""
        result = pipeline._build_system_prompt_for_chat(2)
        assert "LANGUAGE SANITY CHECK" in result
        assert "entirely in English" in result


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
        assert Creativity.CONSERVATIVE == 1
        assert Creativity.DEFAULT == 2
        assert Creativity.SELECTIVE == 3

    def test_name_lookup(self) -> None:
        assert Creativity(0).name == "STRICT"
        assert Creativity(1).name == "CONSERVATIVE"
        assert Creativity(2).name == "DEFAULT"
        assert Creativity(3).name == "SELECTIVE"


class TestPromptHardening:
    """Tests for prompt hardening — injection protection, anti-fabrication, etc."""

    def test_prompt_injection_protection_present(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes injection protection warning for job listing content."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "PROMPT INJECTION" in result
        assert "UNTRUSTED" in result

    def test_anti_fabrication_rule_present(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes the TRUTH GUARD anti-fabrication rule."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "TRUTH GUARD" in result
        assert "Do NOT invent" in result

    def test_inferred_framing_present(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes inferred experience framing rules at level 2+."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "INFERRED EXPERIENCE FRAMING" in result
        assert "transferable" in result.lower()

    def test_length_guidance_present(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes bullet count ceiling guidance."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "BULLET COUNT CEILING" in result

    def test_no_soft_fabrication_in_level_3(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 3 prompt does NOT mention SOFT FABRICATION."""
        result = _build_prompt(base_cv, sample_job_text, 3)
        assert "SOFT FABRICATION" not in result
        assert "TRUTH GUARD" in result

    def test_chat_prompt_has_injection_protection(self) -> None:
        """Chat system prompt includes injection protection."""
        result = pipeline._build_system_prompt_for_chat(2)
        assert "PROMPT INJECTION" in result

    def test_chat_prompt_has_anti_fabrication(self) -> None:
        """Chat system prompt includes anti-fabrication rule."""
        result = pipeline._build_system_prompt_for_chat(2)
        assert "TRUTH GUARD" in result


class TestHighlightedTechnologies:
    """Tests for the deterministic highlighted_technologies rule."""

    def test_rule_resolved_at_level_0(self) -> None:
        """The highlighted_tech rule is present at all levels."""
        result = _resolve_rule("highlighted_tech", 0)
        assert "3-8 CONCRETE tools" in result
        assert "plain names only" in result.lower()

    def test_in_prompt_at_level_2(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """The full prompt includes highlighted tech instructions at level 2."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "3-8 CONCRETE tools" in result

    def test_in_chat_prompt(self) -> None:
        """Chat system prompt includes highlighted tech instructions."""
        result = pipeline._build_system_prompt_for_chat(2)
        assert "3-8 CONCRETE tools" in result

    def test_static_string_replaced(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """The old bare-string 'Surface known-but-not-leading' is gone."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "Surface known-but-not-leading technologies" not in result


class TestUserNotes:
    """Tests for user_notes parameter in prompt builders."""

    def test_user_notes_appear_in_prompt(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """When user_notes is non-empty, it appears in the prompt."""
        result = _build_prompt(base_cv, sample_job_text, 2, user_notes="Emphasize platform work.")
        assert "USER NOTES (user guidance" in result
        assert "Emphasize platform work." in result

    def test_no_user_notes_no_section(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """When user_notes is empty, no USER NOTES heading appears (only injection-rule mention)."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        # The injection rule mentions "user notes" in prose, but the actual
        # USER NOTES heading block should NOT be present.
        assert "USER NOTES (user guidance" not in result

    def test_user_notes_in_user_prompt(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """User prompt includes USER NOTES section when provided."""
        result = pipeline._build_user_prompt(base_cv, sample_job_text, user_notes="Make it concise.")
        assert "USER NOTES" in result
        assert "Make it concise." in result

    def test_no_user_notes_in_user_prompt(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """User prompt does NOT include USER NOTES when empty."""
        result = pipeline._build_user_prompt(base_cv, sample_job_text)
        assert "USER NOTES" not in result

    def test_run_pipeline_accepts_user_notes(self, monkeypatch, base_cv: BaseCV, sample_job_text: str) -> None:
        """run_pipeline accepts and passes user_notes through."""
        monkeypatch.setattr(pipeline, "subprocess", _mock_subprocess(
            lambda cmd, **kw: _make_proc(TAILORED_CV_JSON)
        ))
        # This should not raise
        result, _ = run_pipeline(base_cv, sample_job_text, user_notes="Test notes")
        assert result.summary == "Python engineer with FastAPI expertise."


# ---------------------------------------------------------------------------
# Model validation tests (Task 1.7)
# ---------------------------------------------------------------------------


class TestKeywordPolicyInPrompt:
    """Tests verifying the keyword policy appears in generated prompts."""

    KEY_PHRASES = [
        "1-2 relevant",
        "MUST be backed",
        "tied to a concrete action",
        "do not dump",
        "keyword stuffing",
    ]

    def test_keyword_policy_in_build_prompt_level_0(
        self, base_cv: BaseCV, sample_job_text: str
    ) -> None:
        prompt = _build_prompt(base_cv, sample_job_text, 0)
        assert "NATURAL KEYWORD EMBEDDING POLICY" in prompt
        for phrase in self.KEY_PHRASES:
            assert phrase.lower() in prompt.lower(), f"Missing: {phrase}"

    def test_keyword_policy_in_build_prompt_level_2(
        self, base_cv: BaseCV, sample_job_text: str
    ) -> None:
        prompt = _build_prompt(base_cv, sample_job_text, 2)
        assert "NATURAL KEYWORD EMBEDDING POLICY" in prompt

    def test_keyword_policy_in_build_prompt_level_3(
        self, base_cv: BaseCV, sample_job_text: str
    ) -> None:
        prompt = _build_prompt(base_cv, sample_job_text, 3)
        assert "NATURAL KEYWORD EMBEDDING POLICY" in prompt

    def test_keyword_policy_in_chat_system_prompt(self) -> None:
        prompt = pipeline._build_system_prompt_for_chat(2)
        assert "NATURAL KEYWORD EMBEDDING POLICY" in prompt

    def test_keyword_policy_in_chat_prompt_all_levels(self) -> None:
        """Keyword policy appears at all creativity levels in chat prompt."""
        for level in range(4):
            prompt = pipeline._build_system_prompt_for_chat(level)
            assert "NATURAL KEYWORD EMBEDDING POLICY" in prompt, (
                f"Missing at level {level}"
            )

    def test_keyword_policy_consistent_across_builders(self) -> None:
        """Keyword policy text should be identical between CLI and chat prompts."""
        cli_prompt = _build_prompt(
            BaseCV.model_validate({
                "contact": {"name": "X", "email": "x@x.com"},
                "summary": "test",
                "experience": [{"company": "C", "title": "T", "start": "2020-01",
                                "bullets": ["test"], "technologies": []}],
                "skills": [], "education": [],
            }),
            "test jd", 2,
        )
        chat_prompt = pipeline._build_system_prompt_for_chat(2)
        # Both should contain the same key phrases
        for phrase in self.KEY_PHRASES:
            assert phrase.lower() in cli_prompt.lower()
            assert phrase.lower() in chat_prompt.lower()

    def test_keyword_policy_resolved_at_all_levels(self) -> None:
        """_resolve_rule returns keyword policy at all levels."""
        for level in range(4):
            rule = _resolve_rule("keyword_policy", level)
            assert "NATURAL KEYWORD EMBEDDING POLICY" in rule
            assert len(rule) > 100  # noqa: PLR2004


# ---------------------------------------------------------------------------
# Bullet strategy in prompt tests (Tasks 2.6, 2.7)
# ---------------------------------------------------------------------------


class TestBulletStrategyInPrompt:
    """Tests verifying the impact/differentiator bullet strategy in prompts."""

    KEY_PHRASES = [
        "IMPACT-DRIVEN BULLET STRATEGY",
        "What + How + Result",
        "DEPTH OVER EXPOSURE",
        "role-weighted",
        "ownership signal",
        "avoid generic bullet",
        "50% core skills",
    ]

    def test_strategy_in_build_prompt_level_0(
        self, base_cv: BaseCV, sample_job_text: str,
    ) -> None:
        prompt = _build_prompt(base_cv, sample_job_text, 0)
        for phrase in self.KEY_PHRASES:
            assert phrase.lower() in prompt.lower(), f"Missing: {phrase}"

    def test_strategy_in_build_prompt_level_2(
        self, base_cv: BaseCV, sample_job_text: str,
    ) -> None:
        prompt = _build_prompt(base_cv, sample_job_text, 2)
        assert "IMPACT-DRIVEN BULLET STRATEGY" in prompt

    def test_strategy_in_chat_system_prompt(self) -> None:
        prompt = pipeline._build_system_prompt_for_chat(2)
        assert "IMPACT-DRIVEN BULLET STRATEGY" in prompt

    def test_strategy_resolved_at_all_levels(self) -> None:
        for level in range(4):
            rule = _resolve_rule("bullet_strategy", level)
            assert "IMPACT-DRIVEN BULLET STRATEGY" in rule
            assert len(rule) > 200  # noqa: PLR2004

class TestRecruiterPlausibilityInPrompt:
    """Tests verifying the recruiter plausibility rule in prompts."""

    def test_plausibility_in_build_prompt(self, base_cv: BaseCV, sample_job_text: str) -> None:
        prompt = _build_prompt(base_cv, sample_job_text, 2)
        assert "RECRUITER PLAUSIBILITY RULES" in prompt
        assert "TRUTHFUL PLACEMENT" in prompt
        assert "NATURAL LANGUAGE" in prompt

    def test_plausibility_in_chat_prompt(self) -> None:
        prompt = pipeline._build_system_prompt_for_chat(2)
        assert "RECRUITER PLAUSIBILITY RULES" in prompt

    def test_plausibility_resolved_at_all_levels(self) -> None:
        for level in range(7):
            rule = _resolve_rule("recruiter_plausibility", level)
            assert "TRUTHFUL PLACEMENT" in rule


# ---------------------------------------------------------------------------
# Technology bolding tests
# ---------------------------------------------------------------------------


class TestTechBolding:
    """Tests for deterministic technology bolding."""

    def _make_tailored(self, bullets: list[str], techs: list[str],
                       highlighted: list[str] | None = None) -> TailoredCV:
        return TailoredCV.model_validate({
            "contact": {"name": "Test", "email": "t@t.com"},
            "summary": "test",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": bullets, "technologies": techs}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
            "highlighted_technologies": highlighted or [],
        })

    def test_single_word_bolding(self) -> None:
        cv = self._make_tailored(
            ["Managed Kubernetes clusters"],
            ["Kubernetes"], ["Kubernetes"],
        )
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        assert "**Kubernetes**" in cv.experience[0].bullets[0]

    def test_multi_word_bolding(self) -> None:
        cv = self._make_tailored(
            ["Built CI/CD with GitHub Actions"],
            ["GitHub Actions"], ["GitHub Actions"],
        )
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        assert "**GitHub Actions**" in cv.experience[0].bullets[0]

    def test_case_insensitive_match(self) -> None:
        cv = self._make_tailored(
            ["managed kubernetes clusters"],
            ["Kubernetes"], ["Kubernetes"],
        )
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        assert "**kubernetes**" in cv.experience[0].bullets[0]

    def test_no_double_bolding(self) -> None:
        cv = self._make_tailored(
            ["Managed **Kubernetes** clusters"],
            ["Kubernetes"], ["Kubernetes"],
        )
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        assert cv.experience[0].bullets[0].count("**") == 2  # one pair

    def test_word_boundary_prevents_partial_match(self) -> None:
        cv = self._make_tailored(
            ["Used Kuberneteses tool"],
            ["Kubernetes"], [],
        )
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        assert "**" not in cv.experience[0].bullets[0]

    def test_alias_resolution_k8s(self) -> None:
        cv = self._make_tailored(
            ["Managed K8s clusters"],
            ["Kubernetes"], [],
        )
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        assert "**K8s**" in cv.experience[0].bullets[0]

    def test_global_highlighted_bolded_in_all_roles(self) -> None:
        cv = TailoredCV.model_validate({
            "contact": {"name": "Test", "email": "t@t.com"},
            "summary": "test",
            "experience": [
                {"company": "C", "title": "T", "start": "2020-01",
                 "bullets": ["Used Docker"], "technologies": []},
                {"company": "D", "title": "T2", "start": "2018-01",
                 "bullets": ["Deployed with Docker"], "technologies": []},
            ],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
            "highlighted_technologies": ["Docker"],
        })
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        assert "**Docker**" in cv.experience[0].bullets[0]
        assert "**Docker**" in cv.experience[1].bullets[0]

    def test_role_specific_tech_bolded_only_in_its_role(self) -> None:
        cv = TailoredCV.model_validate({
            "contact": {"name": "Test", "email": "t@t.com"},
            "summary": "test",
            "experience": [
                {"company": "C", "title": "T", "start": "2020-01",
                 "bullets": ["Used Python and Docker"],
                 "technologies": ["Python"]},
                {"company": "D", "title": "T2", "start": "2018-01",
                 "bullets": ["Deployed with Docker"],
                 "technologies": ["Docker"]},
            ],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        # Python bolded in role C only (role tech, not highlighted)
        assert "**Python**" in cv.experience[0].bullets[0]
        # Docker bolded in role D
        assert "**Docker**" in cv.experience[1].bullets[0]

    # ── Allowlist bolding tests ──────────────────────────────────────

    def test_allowlisted_tool_bolded_even_absent_from_tech_fields(self) -> None:
        """Concrete tools in bullets get bolded even if not in technology lists."""
        cv = TailoredCV.model_validate({
            "contact": {"name": "Test", "email": "t@t.com"},
            "summary": "test",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["Deployed apps with ArgoCD and Helm"],
                            "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        bullet = cv.experience[0].bullets[0]
        assert "**ArgoCD**" in bullet
        assert "**Helm**" in bullet

    def test_generic_concepts_not_bolded(self) -> None:
        """Generic concepts like 'automation', 'infrastructure' are NOT bolded."""
        cv = TailoredCV.model_validate({
            "contact": {"name": "Test", "email": "t@t.com"},
            "summary": "test",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": ["Built automation for infrastructure monitoring and scalability"],
                            "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        bullet = cv.experience[0].bullets[0]
        assert "**automation**" not in bullet
        assert "**infrastructure**" not in bullet
        assert "**monitoring**" not in bullet
        assert "**scalability**" not in bullet

    def test_aws_s3_sqs_keda_sentence_all_bolded(self) -> None:
        """Complex sentence with AWS/S3/SQS/KEDA/Kubernetes bolds all concrete tools."""
        cv = TailoredCV.model_validate({
            "contact": {"name": "Test", "email": "t@t.com"},
            "summary": "test",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": [
                                "Designed an event-driven AWS pipeline using S3, SQS, "
                                "and KEDA to autoscale Kubernetes workloads"
                            ],
                            "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        bullet = cv.experience[0].bullets[0]
        assert "**AWS**" in bullet
        assert "**S3**" in bullet
        assert "**SQS**" in bullet
        assert "**KEDA**" in bullet
        assert "**Kubernetes**" in bullet

    def test_argocd_github_actions_terraform_sentence_all_bolded(self) -> None:
        """ArgoCD + GitHub Actions + Terraform all bolded from allowlist."""
        cv = TailoredCV.model_validate({
            "contact": {"name": "Test", "email": "t@t.com"},
            "summary": "test",
            "experience": [{"company": "C", "title": "T", "start": "2020-01",
                            "bullets": [
                                "Built GitOps pipeline with ArgoCD, GitHub Actions, and Terraform"
                            ],
                            "technologies": []}],
            "skills": [],
            "education": [{"institution": "U", "degree": "B"}],
        })
        from core.pipeline import apply_tech_bolding
        apply_tech_bolding(cv)
        bullet = cv.experience[0].bullets[0]
        assert "**ArgoCD**" in bullet
        assert "**GitHub Actions**" in bullet
        assert "**Terraform**" in bullet


# ---------------------------------------------------------------------------
# Modern ATS & Recruiter AI Screening prompt tests
# ---------------------------------------------------------------------------


class TestModernAtsAndRecruiterPromptUpgrades:
    """Tests verifying modern ATS vector clustering, recruiter red-teaming, and anti-AI rules."""

    def test_banned_ai_verbs_in_tone_rule(self) -> None:
        """Tone rule bans common AI buzzwords like 'spearheaded' and 'leveraged'."""
        tone_rule = _resolve_rule("tone", 2)
        assert "BANNED AI VERBS" in tone_rule
        assert "spearheaded" in tone_rule
        assert "orchestrated" in tone_rule
        assert "leveraged" in tone_rule
        assert "built" in tone_rule
        assert "BANNED SYNTACTIC PATTERNS" in tone_rule

    def test_summary_anchor_formula_in_summary_rule(self) -> None:
        """Summary rules enforce the 3-part high-converting anchor formula."""
        for level in (2, 3, 4):
            summary_rule = _resolve_rule("summary", level)
            assert "3-Part High-Converting Anchor Formula" in summary_rule or (
                "3-Part High-Converting" in summary_rule
            )
            assert "Professional Anchor" in summary_rule
            assert "Core Stack Matrix" in summary_rule
            assert "Scale" in summary_rule

    def test_semantic_cooccurrence_in_keyword_policy(self) -> None:
        """Keyword policy includes semantic co-occurrence clusters for vector ATS."""
        rule = _resolve_rule("keyword_policy", 0)
        assert "SEMANTIC CO-OCCURRENCE" in rule
        assert "Kubernetes: pair with Helm" in rule
        assert "Terraform: pair with modules" in rule

    def test_google_xyz_and_scale_fallback_in_bullet_strategy(self) -> None:
        """Bullet strategy includes Google XYZ formula, safe scale fallback, and recency."""
        rule = _resolve_rule("bullet_strategy", 0)
        assert "GOOGLE XYZ FORMULA & FRONT-LOADING" in rule
        assert "NON-NUMERIC SCALE FALLBACK" in rule
        assert "NEVER introduce advanced architectural scopes" in rule
        assert "ROLE-WEIGHTED DISTRIBUTION & RECENCY" in rule
        assert "60-70%" not in rule
        assert "Do NOT move or fabricate technologies into a recent role" in rule

    def test_recruiter_red_team_audit_in_prompts(
        self, base_cv: BaseCV, sample_job_text: str
    ) -> None:
        """Recruiter red-team audit is present and consistently forbids summary bolding."""
        cli_prompt = _build_prompt(base_cv, sample_job_text, 2)
        chat_prompt = pipeline._build_system_prompt_for_chat(2)

        assert "RECRUITER RED-TEAM AUDIT" in cli_prompt
        assert "6-Second Glance" in cli_prompt
        assert "AI-Cliché Check" in cli_prompt
        assert "Defensibility" in cli_prompt
        assert "no markdown bold in summary" in cli_prompt.lower()

        assert "RECRUITER RED-TEAM AUDIT" in chat_prompt
        assert "6-Second Glance" in chat_prompt
        assert "no markdown bold in summary" in chat_prompt.lower()

    def test_modular_terraform_style_anchor_in_prompts(
        self, base_cv: BaseCV, sample_job_text: str
    ) -> None:
        """Both prompt templates include evidence-grounded Terraform anchor without unverified scopes."""
        cli_prompt = _build_prompt(base_cv, sample_job_text, 2)
        chat_prompt = pipeline._build_system_prompt_for_chat(2)

        assert "Engineered modular **Terraform** configurations" in cli_prompt
        assert "BASE EVIDENCE:" in cli_prompt
        assert "Engineered modular **Terraform** configurations" in chat_prompt
        assert "BASE EVIDENCE:" in chat_prompt

        # Verify no ungrounded scopes in the style anchor example
        anchor_block = cli_prompt[
            cli_prompt.find("Configured Terraform") : cli_prompt.find("BULLET ORDERING")
        ]
        assert "multi-AZ" not in anchor_block
        assert "EKS" not in anchor_block
        assert "drift" not in anchor_block

    def test_older_role_technology_not_migrated_rule(self) -> None:
        """Rules explicitly forbid migrating technologies from older roles into recent roles."""
        rule = _resolve_rule("bullet_strategy", 0)
        assert "Do NOT move or fabricate technologies into a recent role" in rule

class TestCategorizedSkillsPrompt:
    """Tests for prompt guidance regarding categorized skills and 15-skill limit."""

    def test_build_prompt_includes_categorized_skills_and_15_cap(
        self, base_cv: BaseCV
    ) -> None:
        prompt = _build_prompt(base_cv, "Need Python and Kubernetes", creativity_level=2)
        assert "SKILLS:" in prompt
        prompt_lower = prompt.lower()
        assert "categories" in prompt_lower or "categorized" in prompt_lower
        assert "15" in prompt
        assert "git" in prompt_lower
        assert "bash" in prompt_lower

    def test_build_system_prompt_includes_categorized_skills(self) -> None:
        sys_prompt = _build_system_prompt_for_chat(creativity_level=2)
        assert "SKILLS:" in sys_prompt
        sys_lower = sys_prompt.lower()
        assert "categories" in sys_lower or "categorized" in sys_lower
        assert "15" in sys_prompt

    def test_user_prompt_schema_has_categorized_skills_hint(
        self, base_cv: BaseCV
    ) -> None:
        user_prompt = _build_user_prompt(base_cv, "Looking for cloud engineers")
        assert '"skills": [' in user_prompt
        prompt_lower = user_prompt.lower()
        assert "category" in prompt_lower or "categories" in prompt_lower
        assert "15" in user_prompt


