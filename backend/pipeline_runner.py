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


def _run_with_staged_fallback(
    provider: BaseProvider, base_cv: BaseCV, job_text: str,
    creativity_level: int, user_notes: str,
) -> tuple[TailoredCV, list[GapItem]]:
    """Try the multi-stage pipeline first; fall back to single-shot run().

    Staged mode (requirements → evidence map → generation) produces better
    keyword grounding but makes 3 model calls. If the provider doesn't
    implement it, or any stage fails after its own retries, fall back to
    the battle-tested single-shot path so the job still completes.
    """
    try:
        return provider.run_staged(base_cv, job_text, creativity_level, user_notes)
    except NotImplementedError:
        logger.info(
            "%s has no run_staged(); using single-shot run()", type(provider).__name__
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Staged pipeline failed on %s (%s); falling back to single-shot run()",
            type(provider).__name__, exc,
        )
    return provider.run(base_cv, job_text, creativity_level, user_notes)


async def run_provider_async(
    provider: BaseProvider, base_cv: BaseCV, job_text: str,
    creativity_level: int = 2,
    user_notes: str = "",
    staged: bool = True,
) -> tuple[TailoredCV, list[GapItem]]:
    """Non-blocking wrapper: runs the provider's synchronous pipeline in thread pool.

    staged=True (default) attempts the multi-stage pipeline with automatic
    fallback to single-shot; staged=False forces single-shot run().
    """
    logger.info(
        "Starting provider %s in thread pool (staged=%s)", type(provider).__name__, staged
    )
    if staged:
        result = await asyncio.to_thread(
            _run_with_staged_fallback, provider, base_cv, job_text, creativity_level, user_notes
        )
    else:
        result = await asyncio.to_thread(
            provider.run, base_cv, job_text, creativity_level, user_notes
        )
    logger.info("Provider %s completed", type(provider).__name__)
    return result


async def render_pdf_async(latex_source: str) -> bytes:
    """Non-blocking wrapper: runs synchronous latexmk compilation in thread pool."""
    logger.info("Starting PDF render in thread pool")
    result = await asyncio.to_thread(render_pdf, latex_source)
    logger.info("PDF render completed (%d bytes)", len(result))
    return result
