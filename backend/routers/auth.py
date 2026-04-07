"""Authentication endpoint — Google ID token exchange for JWT."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.auth import create_jwt, verify_google_token
from backend.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleAuthRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    jwt: str
    user: dict  # {id, email, name, picture}


@router.post("")
async def google_auth(body: GoogleAuthRequest) -> AuthResponse:
    """Exchange a Google ID token for an application JWT.

    Verifies the Google token, upserts the user in the database,
    and returns a signed JWT alongside the user profile.

    Per D-04: user upsert on sign-in creates user on first sign-in,
    updates email/name on subsequent sign-ins.
    """
    # Verify the Google ID token
    try:
        google_info = verify_google_token(body.id_token)
    except ValueError as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Google token") from exc

    google_id = google_info["sub"]
    email = google_info["email"]
    name = google_info.get("name", "")
    picture = google_info.get("picture", "")

    # Upsert user into DB — create on first sign-in, update email/name on subsequent
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO users (google_id, email, name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(google_id) DO UPDATE SET email=excluded.email, name=excluded.name
            """,
            (google_id, email, name, datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()

        # Fetch the user row to get the auto-assigned ID
        cursor = await db.execute(
            "SELECT id, google_id, email, name FROM users WHERE google_id=?",
            (google_id,),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None:
        logger.error("User upsert succeeded but row not found for google_id=%s", google_id)
        raise HTTPException(status_code=500, detail="User creation failed")

    user_id = row["id"]
    token = create_jwt(user_id=user_id, email=email, name=name, picture=picture)

    logger.info("User signed in: id=%s email=%s", user_id, email)

    return AuthResponse(
        jwt=token,
        user={"id": user_id, "email": email, "name": name, "picture": picture},
    )
