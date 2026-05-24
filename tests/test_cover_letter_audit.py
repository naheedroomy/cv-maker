"""Tests for core/cover_letter_audit.py — regex-based AI-tell scanner."""
from __future__ import annotations

from core.cover_letter_audit import audit_cover_letter


class TestAuditCoverLetter:
    def test_clean_text_has_no_warnings(self) -> None:
        text = (
            "Hi,\n\n"
            "Your listing mentions scaling payments infrastructure. I spent the last "
            "two years doing that at my previous role. We went from handling 2K to 40K "
            "requests per second by rebuilding the caching layer.\n\n"
            "Before that I built the observability stack. Prometheus, Grafana, PagerDuty "
            "integration. The team shipped faster because they could see what was happening.\n\n"
            "Happy to walk through the architecture if useful."
        )
        result = audit_cover_letter(text)
        assert result["is_clean"]

    def test_detects_em_dash(self) -> None:
        text = "I led the infrastructure team — it was a pivotal moment for the company."
        result = audit_cover_letter(text)
        assert not result["is_clean"]
        assert any("em_dash" in str(s) for s in result["style_tells"])

    def test_detects_ai_vocab(self) -> None:
        text = "This role is a pivotal testament to the evolving landscape of cloud computing, showcasing intricate details."
        result = audit_cover_letter(text)
        assert not result["is_clean"]
        # Should find at least "pivotal" or "testament" or "showcase"
        assert len(result["ai_vocab_hits"]) > 0

    def test_detects_generic_closing(self) -> None:
        text = (
            "I have experience with Kubernetes and CI/CD.\n\n"
            "I look forward to discussing how I can contribute to your team."
        )
        result = audit_cover_letter(text)
        assert not result["is_clean"]
        assert len(result["generic_closings"]) > 0

    def test_reports_word_and_paragraph_counts(self) -> None:
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = audit_cover_letter(text)
        assert result["word_count"] > 0
        assert result["paragraph_count"] >= 3

    def test_detects_delve(self) -> None:
        text = "I would love to delve into the details of your infrastructure."
        result = audit_cover_letter(text)
        assert any("delve" in str(h) for h in result["ai_vocab_hits"])

    def test_detects_filler_phrase(self) -> None:
        text = "In order to succeed, we built the pipeline."
        result = audit_cover_letter(text)
        assert any("in order to" in str(h).lower() for h in result["ai_vocab_hits"])
