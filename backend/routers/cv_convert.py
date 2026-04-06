"""CV converter API endpoint — POST /api/cv/convert."""
from __future__ import annotations

import asyncio
import logging

import yaml
from fastapi import APIRouter, HTTPException

from backend.schemas import CvConvertRequest, CvConvertResponse
from cv_maker.cv_converter import convert_cv_to_yaml, save_base_cv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/convert", response_model=CvConvertResponse)
async def convert_cv(body: CvConvertRequest) -> CvConvertResponse:
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
