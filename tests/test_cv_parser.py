"""Tests for enhanced vision PDF parser in core/cv_parser.py."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import fitz  # pymupdf
import pytest

from core.cv_parser import _extract_pdf_pages, parse_pdf_to_base_cv
from core.models import BaseCV


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generate synthetic in-memory PDF with text using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 50),
        "Jane Doe\njane.doe@example.com\n+1 555-0199\n"
        "https://linkedin.com/in/janedoe\nhttps://github.com/janedoe\n"
        "Software Engineer with 5 years experience.",
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def sample_cv_dict() -> dict:
    """Valid CV dictionary adhering to BaseCV schema."""
    return {
        "contact": {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "linkedin": "https://linkedin.com/in/janedoe",
            "github": "https://github.com/janedoe",
            "phone": "+1 555-0199",
            "location": "San Francisco, CA",
            "work_authorization": "US Citizen",
        },
        "summary": "Software Engineer with 5 years experience building distributed systems.",
        "experience": [
            {
                "company": "Acme Corp",
                "title": "Senior Software Engineer",
                "location": "San Francisco, CA",
                "start": "2021-03",
                "end": None,
                "bullets": [
                    "Designed and deployed microservices architecture handling 10M daily requests.",
                    "Optimized database indexing improving p99 query latency by 45%.",
                ],
                "technologies": ["Python", "FastAPI", "PostgreSQL"],
            }
        ],
        "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
        "education": [
            {
                "institution": "Tech University",
                "degree": "BSc",
                "field": "Computer Science",
                "year": 2020,
            }
        ],
        "projects": [
            {
                "name": "Cloud Monitor",
                "description": "Real-time metrics dashboard.",
                "technologies": ["Go", "React"],
                "url": "https://github.com/janedoe/cloud-monitor",
            }
        ],
        "certifications": ["AWS Certified Solutions Architect"],
        "languages": [
            {
                "language": "English",
                "level": "Native",
            }
        ],
    }


def test_extract_pdf_pages(sample_pdf_bytes: bytes):
    """Verify _extract_pdf_pages extracts high-res PNG image bytes and native text."""
    pages = _extract_pdf_pages(sample_pdf_bytes, dpi=300)
    assert len(pages) == 1
    page = pages[0]
    assert "image" in page
    assert "images" in page
    assert "text" in page
    assert isinstance(page["image"], bytes)
    assert len(page["image"]) > 0
    assert len(page["images"]) > 0
    assert page["images"][0] == page["image"]
    assert "Jane Doe" in page["text"]
    assert "jane.doe@example.com" in page["text"]


@pytest.mark.asyncio
async def test_parse_pdf_gemini_vision(sample_pdf_bytes: bytes, sample_cv_dict: dict):
    """Verify Gemini vision parsing with mocked Client."""
    with patch("core.cv_parser.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = json.dumps(sample_cv_dict)
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        res = await parse_pdf_to_base_cv(
            sample_pdf_bytes,
            provider="gemini",
            api_key="test-api-key",
        )

        assert isinstance(res, BaseCV)
        assert res.contact.name == "Jane Doe"
        assert res.contact.email == "jane.doe@example.com"
        assert len(res.experience) == 1

        mock_client_cls.assert_called_once_with(api_key="test-api-key")
        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.5-flash"
        contents = call_kwargs["contents"]
        # Must contain image parts and text prompt
        assert len(contents) >= 2


@pytest.mark.asyncio
async def test_parse_pdf_gemini_custom_model_and_env_key(
    sample_pdf_bytes: bytes, sample_cv_dict: dict, monkeypatch: pytest.MonkeyPatch
):
    """Verify Gemini vision parsing uses custom model and GEMINI_API_KEY from environment."""
    monkeypatch.setenv("GEMINI_API_KEY", "env-gemini-key")
    with patch("core.cv_parser.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = json.dumps(sample_cv_dict)
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        res = await parse_pdf_to_base_cv(
            sample_pdf_bytes,
            provider="gemini",
            model="gemini-2.5-pro",
        )

        assert isinstance(res, BaseCV)
        mock_client_cls.assert_called_once_with(api_key="env-gemini-key")
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_parse_pdf_openai_vision(sample_pdf_bytes: bytes, sample_cv_dict: dict):
    """Verify OpenAI vision parsing with mocked AsyncOpenAI."""
    with patch("core.cv_parser.openai.AsyncOpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(sample_cv_dict)
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_openai_cls.return_value = mock_client

        res = await parse_pdf_to_base_cv(
            sample_pdf_bytes,
            provider="openai",
            api_key="test-openai-key",
        )

        assert isinstance(res, BaseCV)
        assert res.contact.name == "Jane Doe"
        assert res.contact.email == "jane.doe@example.com"

        mock_openai_cls.assert_called_once_with(api_key="test-openai-key")
        mock_client.chat.completions.create.assert_awaited_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        messages = call_kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        content_items = messages[1]["content"]
        # Image URL part + text part
        has_image = any(item.get("type") == "image_url" for item in content_items)
        has_text = any(
            item.get("type") == "text" and "EXACT EXTRACTED TEXT FROM PDF" in item.get("text", "")
            for item in content_items
        )
        assert has_image
        assert has_text


@pytest.mark.asyncio
async def test_parse_pdf_openai_custom_model_and_env_key(
    sample_pdf_bytes: bytes, sample_cv_dict: dict, monkeypatch: pytest.MonkeyPatch
):
    """Verify OpenAI vision parsing uses custom model and OPENAI_API_KEY from env."""
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    with patch("core.cv_parser.openai.AsyncOpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(sample_cv_dict)
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_openai_cls.return_value = mock_client

        res = await parse_pdf_to_base_cv(
            sample_pdf_bytes,
            provider="openai",
            model="gpt-4o-mini",
        )

        assert isinstance(res, BaseCV)
        mock_openai_cls.assert_called_once_with(api_key="env-openai-key")
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_parse_pdf_missing_gemini_key_raises(
    sample_pdf_bytes: bytes, monkeypatch: pytest.MonkeyPatch
):
    """Verify missing Gemini API key raises RuntimeError."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured for CV parsing"):
        await parse_pdf_to_base_cv(sample_pdf_bytes, provider="gemini")


@pytest.mark.asyncio
async def test_parse_pdf_missing_openai_key_raises(
    sample_pdf_bytes: bytes, monkeypatch: pytest.MonkeyPatch
):
    """Verify missing OpenAI API key raises RuntimeError."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY not configured for CV parsing"):
        await parse_pdf_to_base_cv(sample_pdf_bytes, provider="openai")


@pytest.mark.asyncio
async def test_parse_pdf_unsupported_provider_raises(sample_pdf_bytes: bytes):
    """Verify unsupported provider raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported parser provider: anthropic"):
        await parse_pdf_to_base_cv(sample_pdf_bytes, provider="anthropic", api_key="any-key")


@pytest.mark.asyncio
async def test_parse_pdf_retry_on_invalid_json(sample_pdf_bytes: bytes, sample_cv_dict: dict):
    """Verify parser retries on malformed JSON then succeeds."""
    with patch("core.cv_parser.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        bad_resp = MagicMock()
        bad_resp.text = "invalid non-json output"
        good_resp = MagicMock()
        good_resp.text = json.dumps(sample_cv_dict)
        mock_client.models.generate_content.side_effect = [bad_resp, good_resp]
        mock_client_cls.return_value = mock_client

        res = await parse_pdf_to_base_cv(
            sample_pdf_bytes,
            provider="gemini",
            api_key="test-key",
        )
        assert res.contact.name == "Jane Doe"
        assert mock_client.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_parse_pdf_fails_after_retries(sample_pdf_bytes: bytes):
    """Verify parser raises RuntimeError after 3 failed attempts."""
    with patch("core.cv_parser.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        bad_resp = MagicMock()
        bad_resp.text = "broken output"
        mock_client.models.generate_content.side_effect = [bad_resp, bad_resp, bad_resp]
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="CV structuring failed after 3 attempts"):
            await parse_pdf_to_base_cv(
                sample_pdf_bytes,
                provider="gemini",
                api_key="test-key",
            )
        assert mock_client.models.generate_content.call_count == 3
