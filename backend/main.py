"""CV Maker FastAPI backend — app entry point.

Run with: uvicorn backend.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles

from backend.db import init_db
from backend.routers.jobs import router as jobs_router

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

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

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


api_router.include_router(jobs_router)
app.include_router(api_router)

# ---------------------------------------------------------------------------
# SPA static files — serve Vue build (only when dist/ exists)
# ---------------------------------------------------------------------------

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA catch-all: serve static files or fall back to index.html."""
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file() and file_path.is_relative_to(FRONTEND_DIST):
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
