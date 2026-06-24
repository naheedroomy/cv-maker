"""Tests for cv_maker.pipeline — all subprocess calls monkeypatched."""
from __future__ import annotations

import json
import subprocess
import types

import pytest

import core.pipeline as pipeline
from core.models import (
    BaseCV,
    EvidenceMap,
    EvidenceMatch,
    GapItem,
    JDRequirement,
    KeywordPair,
    KeywordPairingPlan,
    RequirementExtraction,
    TailoredCV,
)
from core.pipeline import (
    Creativity,
    _build_prompt,
    _resolve_rule,
    extract_requirements,
    generate_tailored_cv,
    map_evidence,
    run_pipeline,
    run_pipeline_staged,
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

    def test_level_3_contains_limited_substitution(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 3 prompt includes limited substitution (one role only) without soft-fabrication."""
        result = _build_prompt(base_cv, sample_job_text, 3)
        assert "LIMITED STACK SUBSTITUTION" in result
        assert "AT MOST 1 role" in result
        assert "No new bullets" in result

    def test_level_4_contains_exposure_language(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 5 prompt includes 'exposure, not ownership' language."""
        result = _build_prompt(base_cv, sample_job_text, 5)
        assert "exposure" in result.lower()

    def test_level_5_contains_fabrication_warning(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 6 prompt includes fabrication warning."""
        result = _build_prompt(base_cv, sample_job_text, 6)
        assert "fabricate" in result.lower()
        assert "WARNING" in result

    def test_level_label_embedded(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Prompt includes the level number and name."""
        result = _build_prompt(base_cv, sample_job_text, 3)
        assert "CREATIVITY LEVEL: 3 (SELECTIVE)" in result

    def test_all_levels_produce_distinct_prompts(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """All 7 levels produce distinct prompt text."""
        prompts = [_build_prompt(base_cv, sample_job_text, i) for i in range(7)]
        assert len(set(prompts)) == 7

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
        """Levels outside 0-6 are clamped."""
        low = _build_prompt(base_cv, sample_job_text, -1)
        zero = _build_prompt(base_cv, sample_job_text, 0)
        assert low == zero
        high = _build_prompt(base_cv, sample_job_text, 99)
        six = _build_prompt(base_cv, sample_job_text, 6)
        assert high == six


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
        assert Creativity.DEFAULT == 2
        assert Creativity.CREATIVE == 6

    def test_name_lookup(self) -> None:
        assert Creativity(3).name == "SELECTIVE"
        assert Creativity(4).name == "FORWARD"


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

    def test_no_soft_fabrication_in_level_4(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """Level 4 prompt does NOT mention SOFT FABRICATION anymore."""
        result = _build_prompt(base_cv, sample_job_text, 4)
        assert "SOFT FABRICATION" not in result
        assert "NO FABRICATION" in result

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
        assert "3-8 specific technologies" in result
        assert "plain names only" in result.lower()

    def test_in_prompt_at_level_2(self, base_cv: BaseCV, sample_job_text: str) -> None:
        """The full prompt includes highlighted tech instructions at level 2."""
        result = _build_prompt(base_cv, sample_job_text, 2)
        assert "3-8 specific technologies" in result

    def test_in_chat_prompt(self) -> None:
        """Chat system prompt includes highlighted tech instructions."""
        result = pipeline._build_system_prompt_for_chat(2)
        assert "3-8 specific technologies" in result

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


class TestIntermediateModels:
    """Tests for the new multi-stage pipeline intermediate Pydantic models."""

    def test_jd_requirement_valid(self) -> None:
        req = JDRequirement(phrase="Kubernetes", category="technology", tier=1)
        assert req.phrase == "Kubernetes"
        assert req.category == "technology"
        assert req.tier == 1
        assert req.related_phrases == []
        assert req.description == ""

    def test_jd_requirement_tier_clamping(self) -> None:
        """Tier must be 1, 2, or 3 — validation should reject others."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            JDRequirement(phrase="Test", tier=4)
        with pytest.raises(Exception):
            JDRequirement(phrase="Test", tier=0)

    def test_jd_requirement_defaults(self) -> None:
        req = JDRequirement(phrase="Python")
        assert req.category == "technology"
        assert req.tier == 2

    def test_evidence_match_strong(self) -> None:
        match = EvidenceMatch(
            requirement_phrase="Kubernetes",
            match_level="strong",
            source_company="CloudCo",
            source_role="Platform Engineer",
            source_bullet_index=0,
            source_field="experience.bullets[0]",
            evidence_text="Managed 50+ clusters",
            allowed_keywords=["Kubernetes"],
        )
        assert match.match_level == "strong"
        assert match.source_bullet_index == 0

    def test_evidence_match_missing(self) -> None:
        match = EvidenceMatch(
            requirement_phrase="Rust",
            match_level="missing",
            evidence_text="",
        )
        assert match.match_level == "missing"
        assert match.source_company is None
        assert match.allowed_keywords == []

    def test_keyword_pair(self) -> None:
        pair = KeywordPair(
            keywords=["Docker", "Kubernetes"],
            rationale="Container orchestration stack",
            evidence_source="TechCorp/Senior Engineer",
            suggested_bullet_count=1,
        )
        assert len(pair.keywords) == 2
        assert pair.suggested_bullet_count == 1

    def test_keyword_pairing_plan_default(self) -> None:
        plan = KeywordPairingPlan()
        assert plan.pairs == []

    def test_requirement_extraction_serialization(self) -> None:
        req = RequirementExtraction(
            requirements=[JDRequirement(phrase="Python", tier=1)],
            raw_jd_hash="abc123",
        )
        data = req.model_dump()
        assert len(data["requirements"]) == 1
        assert data["raw_jd_hash"] == "abc123"

    def test_evidence_map_coverage_summary(self) -> None:
        em = EvidenceMap(
            matches=[
                EvidenceMatch(requirement_phrase="A", match_level="strong",
                              evidence_text="test"),
                EvidenceMatch(requirement_phrase="B", match_level="missing",
                              evidence_text=""),
            ],
            coverage_summary={"total_requirements": 2, "strong_matches": 1,
                              "partial_matches": 0, "missing": 1},
        )
        assert em.coverage_summary["strong_matches"] == 1
        assert em.coverage_summary["missing"] == 1

    # — 1.3-1.5: New optional fields on EvidenceMatch ────────────────

    def test_evidence_match_new_fields_default_empty(self) -> None:
        """differentiator_categories and impact_signals default to empty lists."""
        match = EvidenceMatch(
            requirement_phrase="Python",
            match_level="strong",
            evidence_text="test",
        )
        assert match.differentiator_categories == []
        assert match.impact_signals == []

    def test_evidence_match_new_fields_independent_instances(self) -> None:
        """Two EvidenceMatch instances have independent list instances."""
        m1 = EvidenceMatch(requirement_phrase="A", match_level="strong",
                           evidence_text="test")
        m2 = EvidenceMatch(requirement_phrase="B", match_level="strong",
                           evidence_text="test")
        m1.differentiator_categories.append("automation")
        assert m2.differentiator_categories == []

    def test_evidence_match_new_fields_from_dict(self) -> None:
        """EvidenceMatch construction with new fields preserves them."""
        match = EvidenceMatch.model_validate({
            "requirement_phrase": "Kubernetes",
            "match_level": "strong",
            "evidence_text": "Managed clusters",
            "differentiator_categories": ["automation", "reliability"],
            "impact_signals": ["improved_consistency"],
        })
        assert "automation" in match.differentiator_categories
        assert "improved_consistency" in match.impact_signals


# ---------------------------------------------------------------------------
# Keyword policy in prompt tests (Tasks 2.4, 2.5)
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

    def test_keyword_policy_in_build_prompt_level_6(
        self, base_cv: BaseCV, sample_job_text: str
    ) -> None:
        prompt = _build_prompt(base_cv, sample_job_text, 6)
        assert "NATURAL KEYWORD EMBEDDING POLICY" in prompt

    def test_keyword_policy_in_chat_system_prompt(self) -> None:
        prompt = pipeline._build_system_prompt_for_chat(2)
        assert "NATURAL KEYWORD EMBEDDING POLICY" in prompt

    def test_keyword_policy_in_chat_prompt_all_levels(self) -> None:
        """Keyword policy appears at all creativity levels in chat prompt."""
        for level in range(7):
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
        for level in range(7):
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
        for level in range(7):
            rule = _resolve_rule("bullet_strategy", level)
            assert "IMPACT-DRIVEN BULLET STRATEGY" in rule
            assert len(rule) > 200  # noqa: PLR2004

    def test_strategy_in_stage_3_prompt(
        self, base_cv: BaseCV,
        expected_requirements: RequirementExtraction,
        expected_evidence_map: EvidenceMap,
    ) -> None:
        """Stage 3 generation prompt includes bullet strategy."""
        captured = []

        def mock_provider(prompt: str) -> str:
            captured.append(prompt)
            return json.dumps({
                "contact": {"name": "Jane Smith", "email": "jane@example.com",
                            "github": "github.com/jane"},
                "summary": "test",
                "experience": [{"company": "TechCorp", "title": "Senior Software Engineer",
                                "start": "2019-03", "end": "2024-01",
                                "bullets": ["test"], "technologies": []}],
                "skills": [],
                "education": [{"institution": "State University", "degree": "BSc"}],
            })

        generate_tailored_cv(
            base_cv, expected_requirements, expected_evidence_map, mock_provider,
        )
        assert "IMPACT-DRIVEN BULLET STRATEGY" in captured[0]


# ---------------------------------------------------------------------------
# Multi-stage pipeline tests (Tasks 6.5, 6.6, 6.7)
# ---------------------------------------------------------------------------


class TestMultiStagePipeline:
    """Tests for the multi-stage pipeline functions with mocked providers."""

    def test_extract_requirements_mocked(self) -> None:
        """extract_requirements with mock provider returns RequirementExtraction."""
        mock_json = json.dumps({
            "requirements": [
                {"phrase": "Python", "category": "technology", "tier": 1,
                 "related_phrases": ["FastAPI"],
                 "description": "Strong Python experience"},
            ],
        })

        def mock_provider(prompt: str) -> str:
            return mock_json

        result = extract_requirements("We need Python developers", mock_provider)
        assert isinstance(result, RequirementExtraction)
        assert len(result.requirements) == 1
        assert result.requirements[0].phrase == "Python"
        assert result.raw_jd_hash != ""

    def test_map_evidence_mocked(
        self, base_cv: BaseCV, expected_requirements: RequirementExtraction,
    ) -> None:
        """map_evidence with mock provider returns EvidenceMap."""
        mock_json = json.dumps({
            "matches": [
                {"requirement_phrase": "Kubernetes", "match_level": "strong",
                 "source_company": "TechCorp", "source_role": "Senior Software Engineer",
                 "source_bullet_index": 0, "source_field": "experience.bullets[0]",
                 "evidence_text": "Built REST APIs", "allowed_keywords": ["Kubernetes"],
                 "inference_rule": None},
            ],
            "pairing_plan": {"pairs": []},
            "coverage_summary": {"total_requirements": 1, "strong_matches": 1,
                                 "partial_matches": 0, "missing": 0},
        })

        def mock_provider(prompt: str) -> str:
            return mock_json

        result = map_evidence(expected_requirements, base_cv, mock_provider)
        assert isinstance(result, EvidenceMap)
        assert len(result.matches) == 1
        assert result.matches[0].match_level == "strong"
        assert result.base_cv_hash != ""

    def test_generate_tailored_cv_mocked(
        self, base_cv: BaseCV, expected_requirements: RequirementExtraction,
        expected_evidence_map: EvidenceMap,
    ) -> None:
        """generate_tailored_cv with mock provider returns TailoredCV."""
        mock_json = json.dumps({
            "contact": {"name": "Jane Smith", "email": "jane@example.com",
                        "github": "github.com/jane"},
            "summary": "Python engineer.",
            "experience": [
                {"company": "TechCorp", "title": "Senior Software Engineer",
                 "start": "2019-03", "end": "2024-01",
                 "bullets": ["Built REST APIs with Python"],
                 "technologies": ["Python"]},
            ],
            "skills": ["Python"],
            "education": [{"institution": "State University", "degree": "BSc"}],
        })

        def mock_provider(prompt: str) -> str:
            return mock_json

        result = generate_tailored_cv(
            base_cv, expected_requirements, expected_evidence_map, mock_provider,
        )
        assert isinstance(result, TailoredCV)
        assert result.summary == "Python engineer."

    def test_run_pipeline_staged_orchestration(
        self, base_cv: BaseCV,
    ) -> None:
        """run_pipeline_staged orchestrates all three stages with mocks."""
        call_count = []

        def mock_provider(prompt: str) -> str:
            call_count.append(1)
            if len(call_count) == 1:
                # Stage 1: requirement extraction
                return json.dumps({
                    "requirements": [
                        {"phrase": "Python", "category": "technology", "tier": 1,
                         "related_phrases": [], "description": "Python required"},
                    ],
                })
            elif len(call_count) == 2:
                # Stage 2: evidence mapping
                return json.dumps({
                    "matches": [
                        {"requirement_phrase": "Python", "match_level": "strong",
                         "source_company": "TechCorp", "source_role": "Senior Software Engineer",
                         "source_bullet_index": 0, "source_field": "experience.bullets[0]",
                         "evidence_text": "Built REST APIs", "allowed_keywords": ["Python"],
                         "inference_rule": None},
                    ],
                    "pairing_plan": {"pairs": []},
                    "coverage_summary": {"total_requirements": 1, "strong_matches": 1,
                                         "partial_matches": 0, "missing": 0},
                })
            else:
                # Stage 3: CV generation
                return json.dumps({
                    "contact": {"name": "Jane Smith", "email": "jane@example.com",
                                "github": "github.com/jane"},
                    "summary": "Python developer.",
                    "experience": [
                        {"company": "TechCorp", "title": "Senior Software Engineer",
                         "start": "2019-03", "end": "2024-01",
                         "bullets": ["Built REST APIs with Python"],
                         "technologies": ["Python"]},
                    ],
                    "skills": ["Python"],
                    "education": [{"institution": "State University", "degree": "BSc"}],
                })

        tailored, gap = run_pipeline_staged(
            base_cv, "We need Python developers", mock_provider,
        )
        assert isinstance(tailored, TailoredCV)
        assert isinstance(gap, list)
        assert len(call_count) == 3  # All three stages invoked

    def test_run_pipeline_staged_returns_same_signature_as_run_pipeline(
        self, base_cv: BaseCV,
    ) -> None:
        """run_pipeline_staged returns (TailoredCV, list[GapItem]) same as run_pipeline."""
        call_count = []

        def mock_provider(prompt: str) -> str:
            call_count.append(1)
            if len(call_count) == 1:
                return json.dumps({
                    "requirements": [{"phrase": "X", "category": "technology", "tier": 1,
                                      "related_phrases": [], "description": "test"}],
                })
            elif len(call_count) == 2:
                return json.dumps({
                    "matches": [{"requirement_phrase": "X", "match_level": "strong",
                                 "evidence_text": "test", "allowed_keywords": ["X"],
                                 "inference_rule": None}],
                    "pairing_plan": {"pairs": []},
                    "coverage_summary": {"total_requirements": 1, "strong_matches": 1,
                                         "partial_matches": 0, "missing": 0},
                })
            else:
                return json.dumps({
                    "contact": {"name": "Jane Smith", "email": "jane@example.com",
                                "github": "github.com/jane"},
                    "summary": "test",
                    "experience": [{"company": "TechCorp", "title": "Senior Software Engineer",
                                    "start": "2019-03", "end": "2024-01",
                                    "bullets": ["test"], "technologies": []}],
                    "skills": [],
                    "education": [{"institution": "State University", "degree": "BSc"}],
                })

        tailored, gap = run_pipeline_staged(base_cv, "JD text", mock_provider, 3)
        assert isinstance(tailored, TailoredCV)
        assert isinstance(gap, list)


class TestMultiStagePromptContent:
    """Tests for prompt content in multi-stage pipeline stages."""

    def test_stage_1_prompt_contains_jd_text(self) -> None:
        """Stage 1 prompt must contain the raw JD text."""
        jd = "We need Kubernetes experts with Terraform experience."
        captured_prompts = []

        def mock_provider(prompt: str) -> str:
            captured_prompts.append(prompt)
            return json.dumps({
                "requirements": [{"phrase": "Kubernetes", "category": "technology",
                                  "tier": 1, "related_phrases": [],
                                  "description": "test"}],
            })

        extract_requirements(jd, mock_provider)
        assert len(captured_prompts) == 1
        assert "Kubernetes experts" in captured_prompts[0]

    def test_stage_3_prompt_does_not_contain_raw_jd(
        self, base_cv: BaseCV,
        expected_requirements: RequirementExtraction,
        expected_evidence_map: EvidenceMap,
    ) -> None:
        """Stage 3 prompt must NOT contain the raw JD text."""
        raw_jd_text = "ORIGINAL JD: We need Kubernetes experts with Terraform experience."
        captured_prompts = []

        def mock_provider(prompt: str) -> str:
            captured_prompts.append(prompt)
            return json.dumps({
                "contact": {"name": "Jane Smith", "email": "jane@example.com",
                            "github": "github.com/jane"},
                "summary": "test",
                "experience": [{"company": "TechCorp", "title": "Senior Software Engineer",
                                "start": "2019-03", "end": "2024-01",
                                "bullets": ["test"], "technologies": []}],
                "skills": [],
                "education": [{"institution": "State University", "degree": "BSc"}],
            })

        generate_tailored_cv(
            base_cv, expected_requirements, expected_evidence_map, mock_provider,
        )
        assert len(captured_prompts) == 1
        assert "ORIGINAL JD" not in captured_prompts[0]
        # Should contain evidence map content instead
        assert "EVIDENCE MAP SUMMARY" in captured_prompts[0]

    def test_stage_3_prompt_contains_keyword_policy(
        self, base_cv: BaseCV,
        expected_requirements: RequirementExtraction,
        expected_evidence_map: EvidenceMap,
    ) -> None:
        """Stage 3 prompt includes the keyword policy."""
        captured_prompts = []

        def mock_provider(prompt: str) -> str:
            captured_prompts.append(prompt)
            return json.dumps({
                "contact": {"name": "Jane Smith", "email": "jane@example.com",
                            "github": "github.com/jane"},
                "summary": "test",
                "experience": [{"company": "TechCorp", "title": "Senior Software Engineer",
                                "start": "2019-03", "end": "2024-01",
                                "bullets": ["test"], "technologies": []}],
                "skills": [],
                "education": [{"institution": "State University", "degree": "BSc"}],
            })

        generate_tailored_cv(
            base_cv, expected_requirements, expected_evidence_map, mock_provider,
        )
        assert "NATURAL KEYWORD EMBEDDING POLICY" in captured_prompts[0]


class TestStage2DifferentiatorFields:
    """Tests for Stage 2 prompt extension with differentiator fields."""

    def test_stage_2_prompt_contains_differentiator_instructions(
        self, base_cv: BaseCV, expected_requirements: RequirementExtraction,
    ) -> None:
        """Stage 2 prompt instructs model to populate differentiator fields."""
        captured_prompts = []

        def mock_provider(prompt: str) -> str:
            captured_prompts.append(prompt)
            return json.dumps({
                "matches": [{"requirement_phrase": "X", "match_level": "strong",
                             "evidence_text": "test", "allowed_keywords": ["X"],
                             "inference_rule": None}],
                "pairing_plan": {"pairs": []},
                "coverage_summary": {"total_requirements": 1, "strong_matches": 1,
                                     "partial_matches": 0, "missing": 0},
            })

        map_evidence(expected_requirements, base_cv, mock_provider)
        prompt = captured_prompts[0]
        assert "differentiator_categories" in prompt
        assert "impact_signals" in prompt
        assert "cost_optimization" in prompt  # valid category label

    def test_mock_stage_2_output_with_differentiator_fields(
        self, base_cv: BaseCV, expected_requirements: RequirementExtraction,
    ) -> None:
        """EvidenceMap with populated differentiator fields is accepted."""
        mock_json = json.dumps({
            "matches": [{
                "requirement_phrase": "Kubernetes",
                "match_level": "strong",
                "source_company": "CloudCo",
                "source_role": "Platform Engineer",
                "source_bullet_index": 0,
                "source_field": "experience.bullets[0]",
                "evidence_text": "Managed 50+ clusters",
                "allowed_keywords": ["Kubernetes"],
                "inference_rule": None,
                "differentiator_categories": ["automation", "reliability"],
                "impact_signals": ["improved_consistency"],
            }],
            "pairing_plan": {"pairs": []},
            "coverage_summary": {"total_requirements": 1, "strong_matches": 1,
                                 "partial_matches": 0, "missing": 0},
        })

        def mock_provider(prompt: str) -> str:
            return mock_json

        result = map_evidence(expected_requirements, base_cv, mock_provider)
        assert result.matches[0].differentiator_categories == ["automation", "reliability"]
        assert result.matches[0].impact_signals == ["improved_consistency"]


class TestStagedPipelineBackwardCompat:
    """Tests verifying backward compatibility with existing run_pipeline()."""

    def test_run_pipeline_still_works(
        self, monkeypatch, base_cv: BaseCV, sample_job_text: str,
    ) -> None:
        """Existing run_pipeline tests pass — signature unchanged."""
        # Use the mock subprocess from existing tests
        mock_subprocess = types.SimpleNamespace(
            run=lambda cmd, **kw: subprocess.CompletedProcess(
                args=["claude", "-p", "..."],
                returncode=0,
                stdout=json.dumps({
                    "contact": {"name": "Jane Smith", "email": "jane@example.com",
                                "github": "github.com/jane"},
                    "summary": "Python engineer with FastAPI expertise.",
                    "experience": [
                        {"company": "TechCorp", "title": "Senior Software Engineer",
                         "start": "2019-03", "end": "2024-01",
                         "bullets": ["Built REST APIs using Python and FastAPI"],
                         "technologies": ["Python", "FastAPI"]},
                    ],
                    "skills": ["Python", "FastAPI"],
                    "education": [{"institution": "State University", "degree": "BSc"}],
                }),
                stderr="",
            ),
            TimeoutExpired=subprocess.TimeoutExpired,
        )
        monkeypatch.setattr(pipeline, "subprocess", mock_subprocess)
        tailored, gap = run_pipeline(base_cv, sample_job_text)
        assert isinstance(tailored, TailoredCV)
        assert isinstance(gap, list)

    def test_run_pipeline_keyword_policy_embedded(
        self, base_cv: BaseCV, sample_job_text: str,
    ) -> None:
        """run_pipeline prompt includes keyword policy even in single-shot mode."""
        prompt = _build_prompt(base_cv, sample_job_text, 3)
        assert "NATURAL KEYWORD EMBEDDING POLICY" in prompt
