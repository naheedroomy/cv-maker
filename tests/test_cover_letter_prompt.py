"""Tests for core/cover_letter.py prompt templates, tone instructions, and model validation."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from core.cover_letter import (
    _TONE_INSTRUCTIONS,
    SYSTEM_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE,
    CoverLetterOutput,
    generate_cover_letter,
)
from core.models import BaseCV, EducationItem, ExperienceItem, GapItem, TailoredCV


def _make_dummy_base_cv() -> BaseCV:
    return BaseCV(
        contact={"name": "Alice Smith", "email": "alice@example.com"},
        summary="Senior Backend Engineer with 6 years experience in distributed systems.",
        experience=[
            ExperienceItem(
                company="Acme Corp",
                title="Senior Software Engineer",
                start="2021-01",
                end=None,
                bullets=[
                    "Rearchitected payment gateway to handle 40K req/s during peak sales.",
                    "Migrated 15 microservices from EC2 to Kubernetes with ArgoCD.",
                ],
                technologies=["Go", "Kubernetes", "PostgreSQL", "Kafka"],
            )
        ],
        skills=["Go", "Python", "Kubernetes", "Kafka", "PostgreSQL"],
        education=[EducationItem(institution="State University", degree="B.S. Computer Science")],
    )


def _make_dummy_tailored_cv() -> TailoredCV:
    return TailoredCV(
        contact={"name": "Alice Smith", "email": "alice@example.com"},
        summary="Senior Backend Engineer specializing in resilient payments platforms and K8s.",
        experience=[
            ExperienceItem(
                company="Acme Corp",
                title="Senior Software Engineer",
                start="2021-01",
                end=None,
                bullets=[
                    "Rearchitected payment gateway to handle 40K req/s with zero timeouts.",
                    "Deployed GitOps delivery pipelines using ArgoCD and Kubernetes.",
                ],
                technologies=["Go", "Kubernetes", "PostgreSQL", "Kafka"],
            )
        ],
        skills=["Go", "Kubernetes", "PostgreSQL", "Kafka", "Distributed Systems"],
        education=[EducationItem(institution="State University", degree="B.S. Computer Science")],
    )


class TestCoverLetterPrompts:
    """Verify prompt formatting, tone coverage, and storyteller templates."""

    def test_all_expected_tones_are_registered(self) -> None:
        expected = {
            "standard",
            "professional",
            "casual",
            "confident",
            "direct",
            "enthusiastic",
            "formal",
        }
        assert set(_TONE_INSTRUCTIONS.keys()) == expected

    def test_system_prompt_formats_cleanly_for_all_tones(self) -> None:
        """Ensure str.format does not fail on literal braces or missing keys."""
        for tone_name, instruction in _TONE_INSTRUCTIONS.items():
            formatted = SYSTEM_PROMPT_TEMPLATE.format(tone_instruction=instruction)
            assert instruction in formatted
            assert "PROMPT INJECTION PROTECTION" in formatted
            assert "NARRATIVE STRUCTURE & FLOW" in formatted
            assert "cover_letter_text" in formatted

    def test_user_prompt_formats_cleanly(self) -> None:
        formatted = USER_PROMPT_TEMPLATE.format(
            base_cv_yaml="name: Alice",
            job_text="Backend Engineer at FinTechCo",
            tailored_cv_json='{"summary": "test"}',
            gap_diff_json="[]",
            user_notes="Highlight payments scaling",
            writing_sample="Short and punchy sample.",
        )
        assert "FinTechCo" in formatted
        assert "Highlight payments scaling" in formatted
        assert "Short and punchy sample." in formatted

    def test_cover_letter_output_pydantic_model(self) -> None:
        payload = {
            "cover_letter_text": "Hi,\n\nI built scaling systems.\n\nBest,\nAlice",
            "self_critique": "Voice is conversational and grounded.",
            "revision_notes": "Polished transitions and removed filler.",
        }
        output = CoverLetterOutput.model_validate(payload)
        assert output.cover_letter_text.startswith("Hi,")
        assert "grounded" in output.self_critique

    def test_generate_cover_letter_mock_provider(self) -> None:
        base_cv = _make_dummy_base_cv()
        tailored_cv = _make_dummy_tailored_cv()
        gap_diff = [
            GapItem(requirement="Go", match_level="strong", evidence="Go experience at Acme Corp")
        ]

        mock_provider = MagicMock()
        mock_provider._model = "claude-3-7-sonnet"
        mock_provider._client.messages.create.return_value = MagicMock(
            content=[
                MagicMock(
                    type="text",
                    text=json.dumps({
                        "cover_letter_text": (
                            "Hi Team,\n\n"
                            "Your listing highlights scaling transaction throughput. At Acme "
                            "Corp, I redesigned our payment engine to sustain 40K req/s during "
                            "peak sales.\n\n"
                            "I would love to discuss how this experience can help your team "
                            "scale.\n\n"
                            "Best,\nAlice"
                        ),
                        "self_critique": "Clean and grounded.",
                        "revision_notes": "Focused on core scaling proof point.",
                    }),
                )
            ]
        )

        with patch("core.cover_letter._extract_json") as mock_extract:
            mock_extract.return_value = {
                "cover_letter_text": "Hi Team,\n\nStory here.\n\nBest,\nAlice",
                "self_critique": "Clean.",
                "revision_notes": "Polished.",
            }
            result = generate_cover_letter(
                provider=mock_provider,
                provider_model="claude-api",
                base_cv=base_cv,
                job_text="FinTech looking for backend scaling expert.",
                tailored_cv=tailored_cv,
                gap_diff=gap_diff,
                user_notes="Focus on peak sales load",
            )
            assert "Story here." in result

    def test_system_prompt_includes_voice_and_tone_precedence(self) -> None:
        prompt = SYSTEM_PROMPT_TEMPLATE.format(tone_instruction="Write directly.")
        assert "VOICE & TONE PRECEDENCE" in prompt
        assert "strictly governs the social register" in prompt

    def test_system_prompt_prioritizes_custom_instructions_in_user_notes(self) -> None:
        prompt = SYSTEM_PROMPT_TEMPLATE.format(tone_instruction="Write directly.")
        assert "custom instructions or notes in USER NOTES" in prompt
        assert "prioritize them while keeping all claims strictly grounded" in prompt

    def test_system_prompt_enforces_base_evidence_for_transferable_architecture(self) -> None:
        prompt = SYSTEM_PROMPT_TEMPLATE.format(tone_instruction="Write directly.")
        assert "ONLY IF the candidate has verified production experience" in prompt
        assert "NEVER assert experience with an equivalent" in prompt
        assert "tool not present in the base CV" in prompt

    def test_cover_letter_request_schema_defaults(self) -> None:
        from backend.schemas import CoverLetterRequest

        req = CoverLetterRequest()
        assert req.tone == "standard"
        assert req.reasoning_effort is None
        assert req.model_id is None
        assert req.user_notes == ""

        req_custom = CoverLetterRequest(
            tone="standard",
            model="gemini-flash",
            model_id="gemini-2.5-pro",
            reasoning_effort="high",
            user_notes="Keep under 250 words",
        )
        assert req_custom.reasoning_effort == "high"
        assert req_custom.model_id == "gemini-2.5-pro"
        assert req_custom.user_notes == "Keep under 250 words"
