"""CV CRUD + upload endpoints.

Provides four endpoints for managing a user's saved CV:
- POST   /cv/upload  — PDF upload + two-pass Gemini parsing, saves to DB
- GET    /cv/me      — Returns user's saved CV from DB
- PUT    /cv/me      — Saves edited CV JSON as YAML to users.base_cv_yaml
- DELETE /cv/me      — Sets base_cv_yaml to NULL
"""
from __future__ import annotations

import logging

import yaml
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import ValidationError

from backend.auth import get_current_user
from backend.db import get_db
from backend.schemas import CvMeResponse, CvUploadResponse
from core.cv_parser import parse_pdf_to_base_cv
from core.models import BaseCV

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"])

_MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=CvUploadResponse)
async def upload_cv(
    file: UploadFile,
    user: dict = Depends(get_current_user),
) -> CvUploadResponse:
    """Upload a PDF and parse it into a BaseCV using two-pass Gemini pipeline.

    Saves the parsed CV as YAML to users.base_cv_yaml for the authenticated user.
    """
    # Validate content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a .pdf file.",
        )

    pdf_bytes = await file.read()

    # Validate file size
    if len(pdf_bytes) > _MAX_PDF_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is 10 MB; received {len(pdf_bytes) // 1024 // 1024} MB.",
        )

    logger.info(
        "CV upload request: user_id=%s, filename=%s, size=%d bytes",
        user["id"],
        file.filename,
        len(pdf_bytes),
    )

    try:
        result = await parse_pdf_to_base_cv(pdf_bytes)
    except RuntimeError as exc:
        logger.warning("CV parsing failed for user_id=%s: %s", user["id"], exc)
        return CvUploadResponse(success=False, message=str(exc))

    # Convert to YAML and save to DB
    cv_yaml = yaml.dump(result.model_dump(), default_flow_style=False, allow_unicode=True)

    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET base_cv_yaml=? WHERE id=?",
            (cv_yaml, user["id"]),
        )
        await db.commit()
    finally:
        await db.close()

    logger.info(
        "CV parsed and saved for user_id=%s: contact=%s, experience=%d, skills=%d",
        user["id"],
        result.contact.name,
        len(result.experience),
        len(result.skills),
    )

    return CvUploadResponse(
        success=True,
        message="CV parsed and saved",
        cv=result.model_dump(),
    )


@router.get("/me", response_model=CvMeResponse)
async def get_cv_me(user: dict = Depends(get_current_user)) -> CvMeResponse:
    """Return the authenticated user's saved CV from DB.

    Returns has_cv=False if no CV has been saved.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT base_cv_yaml FROM users WHERE id=?",
            (user["id"],),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None or row["base_cv_yaml"] is None:
        return CvMeResponse(has_cv=False)

    try:
        raw = yaml.safe_load(row["base_cv_yaml"])
        base_cv = BaseCV.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse saved base_cv_yaml for user_id=%s: %s", user["id"], exc)
        return CvMeResponse(has_cv=False)

    return CvMeResponse(has_cv=True, cv=base_cv.model_dump())


@router.put("/me")
async def put_cv_me(body: dict, user: dict = Depends(get_current_user)) -> dict:
    """Save an edited CV for the authenticated user.

    Validates the request body against the BaseCV model before saving.
    Returns 422 if the body is not a valid BaseCV.
    """
    try:
        validated = BaseCV.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    cv_yaml = yaml.dump(validated.model_dump(), default_flow_style=False, allow_unicode=True)

    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET base_cv_yaml=? WHERE id=?",
            (cv_yaml, user["id"]),
        )
        await db.commit()
    finally:
        await db.close()

    logger.info("CV updated for user_id=%s", user["id"])
    return {"success": True, "message": "CV saved"}


@router.delete("/me")
async def delete_cv_me(user: dict = Depends(get_current_user)) -> dict:
    """Remove the authenticated user's saved CV.

    Sets base_cv_yaml to NULL in the DB (reverts to YAML file fallback).
    """
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET base_cv_yaml=NULL WHERE id=?",
            (user["id"],),
        )
        await db.commit()
    finally:
        await db.close()

    logger.info("CV removed for user_id=%s", user["id"])
    return {"success": True, "message": "CV removed"}
