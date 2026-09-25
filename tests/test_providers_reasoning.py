"""Unit tests for reasoning effort / thinking config translation in providers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.models import BaseCV
from core.providers.claude_api_provider import ClaudeAPIProvider
from core.providers.gemini_provider import GeminiProvider
from core.providers.openai_provider import OpenAIProvider

SAMPLE_CV = BaseCV(
    contact={"name": "Alice Developer", "email": "alice@example.com"},
    summary="Software Engineer with Python experience",
    experience=[],
    skills=["Python", "FastAPI"],
    education=[],
)


def _mock_tailored_json():
    return (
        '{"contact": {"name": "Alice Developer", "email": "alice@example.com"}, '
        '"summary": "Tailored summary", "experience": [], "skills": ["Python"], '
        '"education": [], "tailoring_notes": [], "gap_diff": []}'
    )


def test_gemini_provider_reasoning_config():
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = _mock_tailored_json()
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        # 1. High reasoning
        provider = GeminiProvider(
            api_key="test-key", model="gemini-3.8-flash", reasoning_effort="high"
        )
        provider.run(SAMPLE_CV, "job text")
        call_config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert call_config.thinking_config is not None
        assert call_config.thinking_config.thinking_level.name == "HIGH"

        # 2. Off reasoning
        provider_off = GeminiProvider(
            api_key="test-key", model="gemini-3.8-flash", reasoning_effort="off"
        )
        provider_off.run(SAMPLE_CV, "job text")
        call_config_off = mock_client.models.generate_content.call_args.kwargs["config"]
        assert call_config_off.thinking_config is not None
        assert call_config_off.thinking_config.thinking_budget == 0

        # 3. Auto reasoning (omitted)
        provider_auto = GeminiProvider(
            api_key="test-key", model="gemini-3.8-flash", reasoning_effort="auto"
        )
        provider_auto.run(SAMPLE_CV, "job text")
        call_config_auto = mock_client.models.generate_content.call_args.kwargs["config"]
        assert call_config_auto.thinking_config is None


def test_claude_provider_reasoning_config():
    with patch("anthropic.Anthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = _mock_tailored_json()
        mock_resp = MagicMock()
        mock_resp.content = [mock_block]
        mock_client.messages.create.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        # 1. Adaptive / High reasoning on Claude 5
        provider = ClaudeAPIProvider(
            api_key="test-key", model="claude-sonnet-5", reasoning_effort="high"
        )
        provider.run(SAMPLE_CV, "job text")
        kwargs = mock_client.messages.create.call_args.kwargs
        assert "thinking" in kwargs
        assert kwargs["thinking"]["type"] == "adaptive"

        # 2. Budget reasoning on Claude 3.7
        provider_37 = ClaudeAPIProvider(
            api_key="test-key", model="claude-3-7-sonnet", reasoning_effort="low"
        )
        provider_37.run(SAMPLE_CV, "job text")
        kwargs_37 = mock_client.messages.create.call_args.kwargs
        assert "thinking" in kwargs_37
        assert kwargs_37["thinking"]["type"] == "enabled"
        assert kwargs_37["thinking"]["budget_tokens"] == 1024

        # 3. Off
        provider_off = ClaudeAPIProvider(
            api_key="test-key", model="claude-sonnet-5", reasoning_effort="off"
        )
        provider_off.run(SAMPLE_CV, "job text")
        kwargs_off = mock_client.messages.create.call_args.kwargs
        assert "thinking" not in kwargs_off or kwargs_off.get("thinking") is None


def test_openai_provider_reasoning_config():
    with patch("openai.OpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = _mock_tailored_json()
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        # 1. Reasoning model with high effort
        provider = OpenAIProvider(
            api_key="test-key", model="gpt-6-sol", reasoning_effort="high"
        )
        provider.run(SAMPLE_CV, "job text")
        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs.get("reasoning_effort") == "high"

        # 2. Non-reasoning model (gpt-4o-mini) ignores reasoning effort to avoid 400
        provider_4o = OpenAIProvider(
            api_key="test-key", model="gpt-4o-mini", reasoning_effort="high"
        )
        provider_4o.run(SAMPLE_CV, "job text")
        kwargs_4o = mock_client.chat.completions.create.call_args.kwargs
        assert "reasoning_effort" not in kwargs_4o

