"""CV Maker FastAPI backend — app entry point.

Run with: uvicorn backend.main:app --reload
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from backend.db import init_db

# ---------------------------------------------------------------------------
# Logging — configure before app creation
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Background task registry — GC-safe strong references (Phase 6 uses this)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database on startup."""
    logger.info("Starting up - initializing database")
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("Shutting down")


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------

app = FastAPI(lifespan=lifespan, title="CV Maker API")

# CORS — allow Vue dev server during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API router
# ---------------------------------------------------------------------------

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def health_check():
    """Health check endpoint — returns service status."""
    logger.info("Health check requested")
    return {"status": "ok", "service": "cv-maker-backend"}


app.include_router(api_router)
