"""CV Maker FastAPI backend — app entry point.

Run with: uvicorn backend.main:app --reload
"""
from __future__ import annotations

import logging

from dotenv import load_dotenv

load_dotenv()
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles

from backend.db import init_db
from backend.routers.config import router as config_router
from backend.routers.cover_letter import router as cover_letter_router
from backend.routers.cv_convert import router as cv_convert_router
from backend.routers.jobs import router as jobs_router
from backend.routers.settings import router as settings_router

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
    from backend.settings_cache import load_settings
    await load_settings()
    from core.data import DEFAULT_CV_PATH, ensure_base_cv_exists
    ensure_base_cv_exists()
    logger.info("Base CV path: %s", DEFAULT_CV_PATH)
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
api_router.include_router(cover_letter_router)
api_router.include_router(cv_convert_router)
api_router.include_router(config_router)
api_router.include_router(settings_router)
app.include_router(api_router)

# ---------------------------------------------------------------------------
# SPA static files — serve Vue build (only when dist/ exists)
# ---------------------------------------------------------------------------

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA catch-all: serve static files or fall back to index.html.

        Skips /api paths — those are handled by the API router above.
        """
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file() and file_path.is_relative_to(FRONTEND_DIST):
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
