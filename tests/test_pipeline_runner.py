# tests/test_pipeline_runner.py
"""Tests for backend/pipeline_runner.py — async wrappers for pipeline and renderer."""
from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, patch

import pytest


def test_run_pipeline_async_is_coroutine() -> None:
    """run_pipeline_async must be an async function."""
    from backend.pipeline_runner import run_pipeline_async

    assert inspect.iscoroutinefunction(run_pipeline_async)


def test_render_pdf_async_is_coroutine() -> None:
    """render_pdf_async must be an async function."""
    from backend.pipeline_runner import render_pdf_async

    assert inspect.iscoroutinefunction(render_pdf_async)


def test_run_pipeline_async_delegates_to_thread(base_cv, sample_job_text) -> None:
    """run_pipeline_async must call asyncio.to_thread with run_pipeline as first arg."""
    from cv_maker.pipeline import run_pipeline

    fake_result = (base_cv, [])
    with patch(
        "backend.pipeline_runner.asyncio.to_thread",
        new_callable=AsyncMock,
        return_value=fake_result,
    ) as mock_to_thread:
        from backend.pipeline_runner import run_pipeline_async

        result = asyncio.run(run_pipeline_async(base_cv, sample_job_text))
        mock_to_thread.assert_called_once()
        args = mock_to_thread.call_args[0]
        assert args[0] is run_pipeline, (
            f"Expected run_pipeline as first arg to asyncio.to_thread, got {args[0]}"
        )
        assert result == fake_result


def test_render_pdf_async_delegates_to_thread() -> None:
    """render_pdf_async must call asyncio.to_thread with render_pdf as first arg."""
    from cv_maker.renderer import render_pdf

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


def test_run_pipeline_async_propagates_exception(base_cv, sample_job_text) -> None:
    """run_pipeline_async must propagate exceptions from the underlying function."""
    with patch(
        "backend.pipeline_runner.asyncio.to_thread",
        new_callable=AsyncMock,
        side_effect=RuntimeError("pipeline failed"),
    ):
        from backend.pipeline_runner import run_pipeline_async

        with pytest.raises(RuntimeError, match="pipeline failed"):
            asyncio.run(run_pipeline_async(base_cv, sample_job_text))
