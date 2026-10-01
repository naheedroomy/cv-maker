"""CV CRUD, multi-base CV endpoints, and PDF upload.

Provides endpoints for managing user Base CVs:
- POST   /cv/upload    — PDF upload + hybrid vision parser, saves to base_cvs
- GET    /cv/list      — List user Base CV metadata (default first)
- POST   /cv           — Create a new Base CV (blank, duplicate, or from dict)
- GET    /cv/me        — Backward-compat: returns user's default saved CV from DB
- PUT    /cv/me        — Backward-compat: saves edited CV JSON as default Base CV
- DELETE /cv/me        — Backward-compat: sets base_cv_yaml to NULL
- POST   /cv/me/pdf    — Backward-compat: renders posted CV to PDF
- GET    /cv/{id}      — Return Base CV detail by ID
- PUT    /cv/{id}      — Update Base CV by ID (name, content, or default)
- DELETE /cv/{id}      — Delete Base CV by ID (guards deleting last CV)
- POST   /cv/{id}/pdf  — Render Base CV by ID (or body override) to PDF
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import yaml
from fastapi import APIRouter, Body, Depends, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError

from backend.auth import get_current_user
from backend.db import get_db
from backend.schemas import (
    BaseCvCreate,
    BaseCvDetail,
    BaseCvMeta,
    BaseCvUpdate,
    CvMeResponse,
    CvUploadResponse,
)
from backend.settings_cache import get_api_key, get_setting
from core.cv_parser import parse_pdf_to_base_cv
from core.models import BaseCV, TailoredCV
from core.renderer import render_latex, render_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"])

_MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB

_BLANK_CV = {
    "contact": {
        "name": "",
        "email": "",
        "linkedin": None,
        "github": None,
        "phone": None,
        "location": None,
        "work_authorization": None,
    },
    "summary": "",
    "experience": [],
    "skills": [],
    "education": [],
    "projects": [],
    "certifications": [],
    "languages": [],
}


@router.post("/upload", response_model=CvUploadResponse)
async def upload_cv(
    file: UploadFile,
    name: str = Form("Uploaded Base CV"),
    provider: str = Form("gemini"),
    model: str | None = Form(None),
    user: dict = Depends(get_current_user),
) -> CvUploadResponse:
    """Upload a PDF and parse it into a BaseCV using vision + text pipeline.

    Saves to base_cvs, and updates users.base_cv_yaml if marked default.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a .pdf file.",
        )

    pdf_bytes = await file.read()
    if len(pdf_bytes) > _MAX_PDF_SIZE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large. Maximum size is 10 MB; "
                f"received {len(pdf_bytes) // 1024 // 1024} MB."
            ),
        )

    provider_clean = (provider or "gemini").strip().lower()
    key_name = "openai_api_key" if provider_clean == "openai" else "gemini_api_key"
    api_key = await get_api_key(key_name, user["id"])

    try:
        result = await parse_pdf_to_base_cv(
            pdf_bytes,
            provider=provider_clean,
            model=model,
            api_key=api_key or None,
        )
    except (RuntimeError, ValueError) as exc:
        logger.warning("CV parsing failed for user_id=%s: %s", user["id"], exc)
        return CvUploadResponse(success=False, message=str(exc))

    cv_yaml = yaml.dump(result.model_dump(), default_flow_style=False, allow_unicode=True)

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM base_cvs WHERE user_id = ?",
            (user["id"],),
        )
        count_row = await cursor.fetchone()
        cv_count = count_row[0] if count_row else 0
        is_default_val = 1 if cv_count == 0 else 0

        cv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.execute("BEGIN IMMEDIATE")
        if is_default_val == 1:
            await db.execute(
                "UPDATE base_cvs SET is_default = 0 WHERE user_id = ?",
                (user["id"],),
            )
            await db.execute(
                "UPDATE users SET base_cv_yaml = ? WHERE id = ?",
                (cv_yaml, user["id"]),
            )

        await db.execute(
            "INSERT INTO base_cvs (id, user_id, name, cv_yaml, is_default, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cv_id, user["id"], name, cv_yaml, is_default_val, now, now),
        )
        await db.commit()
    finally:
        await db.close()

    logger.info(
        "CV parsed and saved for user_id=%s: id=%s, name=%s, is_default=%d",
        user["id"],
        cv_id,
        name,
        is_default_val,
    )

    return CvUploadResponse(
        success=True,
        message="CV parsed and saved",
        cv=result.model_dump(),
        base_cv_id=cv_id,
        name=name,
    )


@router.get("/list", response_model=list[BaseCvMeta])
async def list_base_cvs(user: dict = Depends(get_current_user)) -> list[BaseCvMeta]:
    """Return all Base CV metadata for the authenticated user, default first."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, name, is_default, created_at, updated_at "
            "FROM base_cvs WHERE user_id = ? "
            "ORDER BY is_default DESC, updated_at DESC",
            (user["id"],),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [
        BaseCvMeta(
            id=row["id"],
            name=row["name"],
            is_default=bool(row["is_default"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.post("", response_model=BaseCvDetail)
async def create_base_cv(
    body: BaseCvCreate,
    user: dict = Depends(get_current_user),
) -> BaseCvDetail:
    """Create a new Base CV.

    If source_id is provided, duplicates existing CV.
    Else if cv dict is provided, validates and converts to YAML.
    Else uses minimal blank template.
    If is_default is true or user has 0 CVs, sets is_default = 1 and unsets others.
    """
    db = await get_db()
    try:
        if body.source_id:
            cursor = await db.execute(
                "SELECT cv_yaml FROM base_cvs WHERE id = ? AND user_id = ?",
                (body.source_id, user["id"]),
            )
            row = await cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Source Base CV not found")
            cv_yaml = row["cv_yaml"]
            try:
                raw = yaml.safe_load(cv_yaml)
                base_cv = BaseCV.model_validate(raw)
            except Exception as exc:
                raise HTTPException(status_code=500, detail="Invalid source CV YAML") from exc
        elif body.cv is not None:
            try:
                base_cv = BaseCV.model_validate(body.cv)
            except ValidationError as exc:
                raise HTTPException(status_code=422, detail=exc.errors()) from exc
            cv_yaml = yaml.dump(base_cv.model_dump(), default_flow_style=False, allow_unicode=True)
        else:
            base_cv = BaseCV.model_validate(_BLANK_CV)
            cv_yaml = yaml.dump(base_cv.model_dump(), default_flow_style=False, allow_unicode=True)

        count_cursor = await db.execute(
            "SELECT COUNT(*) FROM base_cvs WHERE user_id = ?",
            (user["id"],),
        )
        count_row = await count_cursor.fetchone()
        cv_count = count_row[0] if count_row else 0
        is_default_val = 1 if (body.is_default or cv_count == 0) else 0

        cv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.execute("BEGIN IMMEDIATE")
        if is_default_val == 1:
            await db.execute(
                "UPDATE base_cvs SET is_default = 0 WHERE user_id = ?",
                (user["id"],),
            )
            await db.execute(
                "UPDATE users SET base_cv_yaml = ? WHERE id = ?",
                (cv_yaml, user["id"]),
            )

        await db.execute(
            "INSERT INTO base_cvs (id, user_id, name, cv_yaml, is_default, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cv_id, user["id"], body.name, cv_yaml, is_default_val, now, now),
        )
        await db.commit()
    finally:
        await db.close()

    return BaseCvDetail(
        id=cv_id,
        name=body.name,
        is_default=bool(is_default_val),
        created_at=now,
        updated_at=now,
        cv=base_cv.model_dump(),
    )


@router.get("/me", response_model=CvMeResponse)
async def get_cv_me(user: dict = Depends(get_current_user)) -> CvMeResponse:
    """Return the authenticated user's saved CV from DB.

    Returns default Base CV from base_cvs (or fallback to users.base_cv_yaml).
    Returns has_cv=False if no CV has been saved.
    """
    db = await get_db()
    try:
        user_cursor = await db.execute(
            "SELECT base_cv_yaml FROM users WHERE id=?",
            (user["id"],),
        )
        user_row = await user_cursor.fetchone()
        if user_row is None or user_row["base_cv_yaml"] is None:
            return CvMeResponse(has_cv=False)

        cv_cursor = await db.execute(
            "SELECT cv_yaml FROM base_cvs WHERE user_id=? AND is_default=1",
            (user["id"],),
        )
        cv_row = await cv_cursor.fetchone()
        chosen_yaml = (
            cv_row["cv_yaml"]
            if cv_row and cv_row["cv_yaml"]
            else user_row["base_cv_yaml"]
        )
    finally:
        await db.close()

    try:
        raw = yaml.safe_load(chosen_yaml)
        base_cv = BaseCV.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse saved CV for user_id=%s: %s", user["id"], exc)
        return CvMeResponse(has_cv=False)

    return CvMeResponse(has_cv=True, cv=base_cv.model_dump())


@router.put("/me")
async def put_cv_me(body: dict, user: dict = Depends(get_current_user)) -> dict:
    """Save an edited CV for the authenticated user.

    Validates the request body against the BaseCV model before saving.
    Updates the user's default Base CV in base_cvs (creating one if none exists)
    and updates users.base_cv_yaml.
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
        cursor = await db.execute(
            "SELECT id FROM base_cvs WHERE user_id=? AND is_default=1",
            (user["id"],),
        )
        row = await cursor.fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if row:
            await db.execute(
                "UPDATE base_cvs SET cv_yaml=?, updated_at=? WHERE id=?",
                (cv_yaml, now, row["id"]),
            )
        else:
            any_cursor = await db.execute(
                "SELECT id FROM base_cvs WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
                (user["id"],),
            )
            any_row = await any_cursor.fetchone()
            if any_row:
                await db.execute(
                    "UPDATE base_cvs SET cv_yaml=?, is_default=1, updated_at=? WHERE id=?",
                    (cv_yaml, now, any_row["id"]),
                )
            else:
                cv_id = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO base_cvs (id, user_id, name, cv_yaml, is_default, "
                    "created_at, updated_at) VALUES (?, ?, 'Main Base CV', ?, 1, ?, ?)",
                    (cv_id, user["id"], cv_yaml, now, now),
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


@router.post("/me/pdf")
async def download_base_cv_pdf(body: dict, user: dict = Depends(get_current_user)) -> Response:
    """Render the current base CV as PDF via the LaTeX pipeline.

    Accepts CV data in request body so unsaved in-memory edits are included.
    Converts BaseCV to TailoredCV (extra fields default to []) for renderer compatibility.
    """
    try:
        base_cv = BaseCV.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    tailored = TailoredCV(**base_cv.model_dump())
    latex_source = render_latex(tailored)
    pdf_bytes = await asyncio.to_thread(render_pdf, latex_source)

    cv_filename = await get_setting("cv_filename", user["id"])
    if not cv_filename:
        cv_filename = base_cv.contact.name.replace(" ", "-") if base_cv.contact.name else "Base-CV"
    filename = f"{cv_filename}.pdf"

    logger.info("PDF rendered for user_id=%s: filename=%s", user["id"], filename)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/{id}", response_model=BaseCvDetail)
async def get_base_cv(id: str, user: dict = Depends(get_current_user)) -> BaseCvDetail:
    """Return full detail of a Base CV by ID for the authenticated user."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, name, cv_yaml, is_default, created_at, updated_at "
            "FROM base_cvs WHERE id = ? AND user_id = ?",
            (id, user["id"]),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Base CV not found")

    try:
        raw = yaml.safe_load(row["cv_yaml"])
        base_cv = BaseCV.model_validate(raw)
    except Exception as exc:
        logger.warning("Failed to parse base CV %s for user %s: %s", id, user["id"], exc)
        raise HTTPException(status_code=500, detail="Failed to parse Base CV data") from exc

    return BaseCvDetail(
        id=row["id"],
        name=row["name"],
        is_default=bool(row["is_default"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        cv=base_cv.model_dump(),
    )


@router.put("/{id}", response_model=BaseCvDetail)
async def update_base_cv(
    id: str,
    body: BaseCvUpdate,
    user: dict = Depends(get_current_user),
) -> BaseCvDetail:
    """Update name, cv, and/or is_default of an existing Base CV."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, name, cv_yaml, is_default, created_at, updated_at "
            "FROM base_cvs WHERE id = ? AND user_id = ?",
            (id, user["id"]),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Base CV not found")

        new_name = body.name if body.name is not None else row["name"]
        if body.cv is not None:
            try:
                base_cv = BaseCV.model_validate(body.cv)
            except ValidationError as exc:
                raise HTTPException(status_code=422, detail=exc.errors()) from exc
            new_cv_yaml = yaml.dump(
                base_cv.model_dump(), default_flow_style=False, allow_unicode=True
            )
            cv_dict = base_cv.model_dump()
        else:
            new_cv_yaml = row["cv_yaml"]
            try:
                cv_dict = yaml.safe_load(new_cv_yaml)
            except Exception:
                cv_dict = {}

        if body.is_default is not None:
            new_is_default = 1 if body.is_default else 0
        else:
            new_is_default = row["is_default"]

        now = datetime.now(timezone.utc).isoformat()

        await db.execute("BEGIN IMMEDIATE")
        if body.is_default is True:
            await db.execute(
                "UPDATE base_cvs SET is_default = 0 WHERE user_id = ?",
                (user["id"],),
            )
            await db.execute(
                "UPDATE users SET base_cv_yaml = ? WHERE id = ?",
                (new_cv_yaml, user["id"]),
            )
        elif new_is_default == 1:
            await db.execute(
                "UPDATE users SET base_cv_yaml = ? WHERE id = ?",
                (new_cv_yaml, user["id"]),
            )

        await db.execute(
            "UPDATE base_cvs SET name = ?, cv_yaml = ?, is_default = ?, updated_at = ? "
            "WHERE id = ? AND user_id = ?",
            (new_name, new_cv_yaml, new_is_default, now, id, user["id"]),
        )
        await db.commit()
    finally:
        await db.close()

    return BaseCvDetail(
        id=id,
        name=new_name,
        is_default=bool(new_is_default),
        created_at=row["created_at"],
        updated_at=now,
        cv=cv_dict,
    )


@router.delete("/{id}")
async def delete_base_cv(id: str, user: dict = Depends(get_current_user)) -> dict:
    """Delete a Base CV.

    Rejects deletion if it is the user's only Base CV.
    If the deleted CV was default, promotes the most recently updated CV to default.
    """
    db = await get_db()
    try:
        count_cursor = await db.execute(
            "SELECT COUNT(*) FROM base_cvs WHERE user_id = ?",
            (user["id"],),
        )
        count_row = await count_cursor.fetchone()
        count = count_row[0] if count_row else 0
        if count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete your only Base CV.")

        cv_cursor = await db.execute(
            "SELECT id, is_default FROM base_cvs WHERE id = ? AND user_id = ?",
            (id, user["id"]),
        )
        cv_row = await cv_cursor.fetchone()
        if cv_row is None:
            raise HTTPException(status_code=404, detail="Base CV not found")

        is_deleted_default = bool(cv_row["is_default"])

        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "DELETE FROM base_cvs WHERE id = ? AND user_id = ?",
            (id, user["id"]),
        )

        if is_deleted_default:
            promote_cursor = await db.execute(
                "SELECT id, cv_yaml FROM base_cvs WHERE user_id = ? "
                "ORDER BY updated_at DESC LIMIT 1",
                (user["id"],),
            )
            next_cv = await promote_cursor.fetchone()
            if next_cv:
                await db.execute(
                    "UPDATE base_cvs SET is_default = 1 WHERE id = ?",
                    (next_cv["id"],),
                )
                await db.execute(
                    "UPDATE users SET base_cv_yaml = ? WHERE id = ?",
                    (next_cv["cv_yaml"], user["id"]),
                )
        await db.commit()
    finally:
        await db.close()

    logger.info("Base CV %s deleted for user_id=%s", id, user["id"])
    return {"success": True, "message": "Base CV deleted"}


@router.post("/{id}/pdf")
async def download_base_cv_by_id_pdf(
    id: str,
    cv_data: dict | None = Body(None),
    user: dict = Depends(get_current_user),
) -> Response:
    """Render the Base CV as PDF via LaTeX pipeline.

    Accepts optional cv_data in request body for unsaved edits; otherwise loads from DB.
    """
    if cv_data:
        data_to_validate = (
            cv_data["cv_data"]
            if ("cv_data" in cv_data and isinstance(cv_data["cv_data"], dict))
            else cv_data
        )
        try:
            base_cv = BaseCV.model_validate(data_to_validate)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        name_hint = base_cv.contact.name
    else:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT cv_yaml, name FROM base_cvs WHERE id = ? AND user_id = ?",
                (id, user["id"]),
            )
            row = await cursor.fetchone()
        finally:
            await db.close()

        if row is None:
            raise HTTPException(status_code=404, detail="Base CV not found")

        try:
            raw = yaml.safe_load(row["cv_yaml"])
            base_cv = BaseCV.model_validate(raw)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to parse Base CV data") from exc
        name_hint = base_cv.contact.name or row["name"]

    tailored = TailoredCV(**base_cv.model_dump())
    latex_source = render_latex(tailored)
    pdf_bytes = await asyncio.to_thread(render_pdf, latex_source)

    cv_filename = await get_setting("cv_filename", user["id"])
    if not cv_filename:
        cv_filename = name_hint.replace(" ", "-") if name_hint else "Base-CV"
    filename = f"{cv_filename}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
