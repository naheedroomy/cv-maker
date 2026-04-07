# tests/test_pipeline_runner.py
"""Tests for backend/pipeline_runner.py — async wrappers for provider and renderer.

Note: run_pipeline_async was removed in quick-260405-o4h (dead export, superseded by
run_provider_async). Tests for that function have been removed accordingly.
"""
from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, patch


def test_render_pdf_async_is_coroutine() -> None:
    """render_pdf_async must be an async function."""
    from backend.pipeline_runner import render_pdf_async

    assert inspect.iscoroutinefunction(render_pdf_async)


def test_render_pdf_async_delegates_to_thread() -> None:
    """render_pdf_async must call asyncio.to_thread with render_pdf as first arg."""
    from core.renderer import render_pdf

    fake_bytes = b"%PDF-1.4 fake"
    with patch(
        "backend.pipeline_runner.asyncio.to_thread",
        new_callable=AsyncMock,
        return_value=fake_bytes,
    ) as mock_to_thread:
        from backend.pipeline_runner import render_pdf_async

        result = asyncio.run(render_pdf_async("\\documentclass{article}"))
        mock_to_thread.assert_called_once()
        args = mock_to_thread.call_args[0]
        assert args[0] is render_pdf, (
            f"Expected render_pdf as first arg to asyncio.to_thread, got {args[0]}"
        )
        assert result == fake_bytes
