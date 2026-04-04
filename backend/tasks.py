"""Background task registry — GC-safe strong references.

Extracted from main.py into its own module to avoid circular imports when
routers need to schedule tasks via schedule_background_task().

Import pattern:
  from backend.tasks import schedule_background_task
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# Module-level set holds strong references so GC doesn't collect live tasks
_background_tasks: set[asyncio.Task[Any]] = set()


def schedule_background_task(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    """Schedule a coroutine as a background task with GC protection.

    The task is stored in _background_tasks to prevent garbage collection.
    On completion (success, failure, or cancellation), the reference is removed.
    """
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    logger.info("Background task scheduled: %s", task.get_name())
    return task
