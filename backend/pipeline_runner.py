"""Async wrappers for the synchronous cv_maker pipeline and renderer.

run_provider_async() and render_pdf_async() call subprocess.run internally,
which blocks the OS thread. asyncio.to_thread() moves each call to the thread
pool executor, preventing the event loop from being blocked.

These wrappers are the ONLY way the backend should call pipeline or renderer
functions. Never call the synchronous versions directly from async def code.
"""
from __future__ import annotations

import asyncio
import logging

from core.models import BaseCV, GapItem, TailoredCV
from core.providers.base import BaseProvider
from core.renderer import render_pdf

logger = logging.getLogger(__name__)


async def run_provider_async(
    provider: BaseProvider, base_cv: BaseCV, job_text: str,
    creativity_level: int = 2,
) -> tuple[TailoredCV, list[GapItem]]:
    """Non-blocking wrapper: runs any provider's synchronous .run() in thread pool."""
    logger.info("Starting provider %s in thread pool", type(provider).__name__)
    result = await asyncio.to_thread(provider.run, base_cv, job_text, creativity_level)
    logger.info("Provider %s completed", type(provider).__name__)
    return result


async def render_pdf_async(latex_source: str) -> bytes:
    """Non-blocking wrapper: runs synchronous latexmk compilation in thread pool."""
    logger.info("Starting PDF render in thread pool")
    result = await asyncio.to_thread(render_pdf, latex_source)
    logger.info("PDF render completed (%d bytes)", len(result))
    return result
