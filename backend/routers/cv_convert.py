"""CV converter API endpoint — POST /api/cv/convert and GET /api/cv/info."""
from __future__ import annotations

import asyncio
import logging

import yaml
from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.schemas import CvConvertRequest, CvConvertResponse
from core.cv_converter import convert_cv_to_yaml, save_base_cv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"])


@router.get("/info")
async def get_cv_info(user: dict = Depends(get_current_user)):
    """Return the full base CV data for preview, plus a loaded flag.

    Checks DB first for user's base_cv_yaml (DB CV takes priority).
    Falls back to YAML file if no CV stored in DB.
    """
    from core.data import DEFAULT_CV_PATH, load_base_cv
    from core.models import BaseCV

    # DB-first: check if user has a saved CV in the database
    from backend.db import get_db

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT base_cv_yaml FROM users WHERE id=?",
            (user["id"],),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row and row["base_cv_yaml"]:
        try:
            import yaml as _yaml
            raw = _yaml.safe_load(row["base_cv_yaml"])
            cv = BaseCV.model_validate(raw)
            return {
                "loaded": True,
                "name": cv.contact.name,
                "roles": len(cv.experience),
                "skills": len(cv.skills),
                "certifications": len(cv.certifications),
                "cv": cv.model_dump(),
                "source": "db",
            }
        except Exception:  # noqa: BLE001
            pass  # Fall through to file fallback

    # File fallback
    if not DEFAULT_CV_PATH.exists():
        return {"loaded": False}

    try:
        cv = await asyncio.to_thread(load_base_cv)
    except Exception:  # noqa: BLE001
        return {"loaded": False}

    return {
        "loaded": True,
        "name": cv.contact.name,
        "roles": len(cv.experience),
        "skills": len(cv.skills),
        "certifications": len(cv.certifications),
        "cv": cv.model_dump(),
        "source": "file",
    }


@router.post("/convert", response_model=CvConvertResponse)
async def convert_cv(body: CvConvertRequest, user: dict = Depends(get_current_user)) -> CvConvertResponse:
    """Parse plain-text CV content into BaseCV YAML and save it as base_cv.yaml.

    Invokes Claude Code CLI via asyncio.to_thread (subprocess call — must not block the
    event loop). Returns a structured response so the frontend can display success/error
    feedback without needing to handle HTTP error codes.

    Returns 500 only for truly unexpected errors (e.g. unhandled exception from a bug).
    Parse failures from Claude are returned as success=False with the error message.
    """
    logger.info("CV convert request received — cv_text length=%d", len(body.cv_text))

    if not body.cv_text.strip():
        return CvConvertResponse(success=False, message="CV text cannot be empty.")

    try:
        # LLM call — run in thread to avoid blocking the event loop
        result = await asyncio.to_thread(convert_cv_to_yaml, body.cv_text, body.model)
    except RuntimeError as exc:
        # Claude parse failure or validation error — return structured error to frontend
        logger.warning("CV conversion failed: %s", exc)
        return CvConvertResponse(success=False, message=str(exc))
    except Exception as exc:  # noqa: BLE001
        # Truly unexpected error — log and return 500
        logger.exception("Unexpected error during CV conversion")
        raise HTTPException(status_code=500, detail="Internal server error") from exc

    try:
        # Disk write — also run in thread since it is I/O
        saved_path = await asyncio.to_thread(save_base_cv, result)
        logger.info("base_cv.yaml saved at %s for contact=%s", saved_path, result.contact.name)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to save base_cv.yaml after successful parse")
        raise HTTPException(status_code=500, detail="Parsed CV but failed to save file") from exc

    yaml_content = yaml.dump(result.model_dump(), default_flow_style=False, allow_unicode=True)

    return CvConvertResponse(
        success=True,
        message="CV parsed and saved as base_cv.yaml",
        contact_name=result.contact.name,
        yaml_content=yaml_content,
    )
