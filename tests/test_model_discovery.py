"""Tests for dynamic model discovery across Gemini, Claude, and OpenAI providers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from backend.main import app
from core.providers.model_discovery import discover_provider_models


@pytest.mark.asyncio
async def test_discover_gemini_models():
    mock_model_1 = MagicMock()
    mock_model_1.name = "models/gemini-2.5-flash"
    mock_model_1.display_name = "Gemini 2.5 Flash"

    mock_model_2 = MagicMock()
    mock_model_2.name = "models/text-embedding-004"
    mock_model_2.display_name = "Text Embedding"

    mock_model_3 = MagicMock()
    mock_model_3.name = "models/gemini-3.8-flash"
    mock_model_3.display_name = "Gemini 3.8 Flash"

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.list.return_value = [mock_model_1, mock_model_2, mock_model_3]
        mock_client_cls.return_value = mock_client

        models = await discover_provider_models("gemini", api_key="test-key")
        assert len(models) == 2
        ids = [m["id"] for m in models]
        assert "gemini-2.5-flash" in ids
        assert "gemini-3.8-flash" in ids
        assert "text-embedding-004" not in ids


@pytest.mark.asyncio
async def test_discover_claude_models():
    mock_m1 = MagicMock()
    mock_m1.id = "claude-haiku-4-5"
    mock_m1.display_name = "Claude Haiku 4.5"

    mock_m2 = MagicMock()
    mock_m2.id = "claude-sonnet-5"
    mock_m2.display_name = "Claude Sonnet 5"

    with patch("anthropic.Anthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_page = MagicMock()
        mock_page.data = [mock_m1, mock_m2]
        mock_client.models.list.return_value = mock_page
        mock_client_cls.return_value = mock_client

        models = await discover_provider_models("claude-api", api_key="test-key")
        assert len(models) == 2
        assert models[0]["id"] == "claude-haiku-4-5"


@pytest.mark.asyncio
async def test_discover_openai_models():
    mock_m1 = MagicMock()
    mock_m1.id = "gpt-4o-mini"

    mock_m2 = MagicMock()
    mock_m2.id = "text-embedding-3-small"

    mock_m3 = MagicMock()
    mock_m3.id = "gpt-6-sol"

    with patch("openai.OpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_page = MagicMock()
        mock_page.data = [mock_m1, mock_m2, mock_m3]
        mock_client.models.list.return_value = mock_page
        mock_client_cls.return_value = mock_client

        models = await discover_provider_models("openai", api_key="test-key")
        assert len(models) == 2
        ids = [m["id"] for m in models]
        assert "gpt-4o-mini" in ids
        assert "gpt-6-sol" in ids
        assert "text-embedding-3-small" not in ids


def test_settings_models_endpoint(tmp_path):
    with patch("core.providers.model_discovery.discover_provider_models") as mock_discover:
        mock_discover.return_value = [{"id": "test-model", "label": "Test Model"}]
        client = TestClient(app)
        res = client.get("/api/settings/models?provider=openai&api_key=sk-test")
        assert res.status_code == 200
        data = res.json()
        assert "models" in data
        assert data["models"][0]["id"] == "test-model"
