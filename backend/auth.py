"""Google OAuth 2.0 token verification + JWT issuance/decoding.

Per D-01: Frontend sends Google ID token to POST /api/auth/google.
Backend verifies with google.oauth2.id_token, issues HS256 JWT with 7-day expiry.
Per D-02: get_current_user() is a FastAPI Depends() — extracts user from Bearer token.
Dev-mode fallback: if GOOGLE_CLIENT_ID is not set, returns ANONYMOUS_USER_ID user.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Header, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from backend.db import ANONYMOUS_USER_ID


def verify_google_token(id_token_str: str) -> dict:
    """Verify a Google ID token and return the user's profile info.

    Args:
        id_token_str: The Google ID token from the frontend sign-in flow.

    Returns:
        Dict with keys: sub (google_id), email, name, picture.

    Raises:
        ValueError: If the token is invalid, expired, or audience doesn't match.
    """
    try:
        audience = os.environ.get("GOOGLE_CLIENT_ID")
        request = google_requests.Request()
        id_info = google_id_token.verify_oauth2_token(
            id_token_str,
            request,
            audience=audience,
        )
        return {
            "sub": id_info["sub"],
            "email": id_info.get("email", ""),
            "name": id_info.get("name", ""),
            "picture": id_info.get("picture", ""),
        }
    except Exception as exc:
        raise ValueError(f"Invalid Google token: {exc}") from exc


def create_jwt(user_id: int, email: str, name: str, picture: str = "") -> str:
    """Create an HS256 JWT with user claims and 7-day expiry.

    Args:
        user_id: Database user ID.
        email: User's email address.
        name: User's display name.
        picture: URL to the user's profile picture (optional).

    Returns:
        Signed JWT string.
    """
    secret = os.environ.get("JWT_SECRET", "dev-secret-change-me")
    payload = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    """Decode and validate an HS256 JWT.

    Args:
        token: JWT string to decode.

    Returns:
        Payload dict with user claims.

    Raises:
        ValueError: If the token is expired or otherwise invalid.
    """
    secret = os.environ.get("JWT_SECRET", "dev-secret-change-me")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Invalid or expired token") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid or expired token") from exc


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """FastAPI dependency — extract the current user from the Authorization header.

    Dev-mode fallback (D-02): If no Authorization header is provided and
    GOOGLE_CLIENT_ID is not set in the environment, returns the anonymous local user
    so that the app is fully usable without auth during local development.

    Production mode: If GOOGLE_CLIENT_ID is set, a missing or invalid Authorization
    header results in HTTP 401.

    Args:
        authorization: Value of the Authorization header (e.g. "Bearer <token>").

    Returns:
        Dict with keys: id, email, name, picture.

    Raises:
        HTTPException 401: If auth is required but token is missing/invalid.
    """
    if not authorization:
        # No token provided — apply dev-mode fallback or production 401
        if not os.environ.get("GOOGLE_CLIENT_ID"):
            # Dev-mode: GOOGLE_CLIENT_ID not configured, return anonymous user
            return {
                "id": ANONYMOUS_USER_ID,
                "email": "local@localhost",
                "name": "Local User",
                "picture": "",
            }
        # Production mode: auth is required
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Strip "Bearer " prefix
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_jwt(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Not authenticated") from exc

    return {
        "id": payload["user_id"],
        "email": payload["email"],
        "name": payload["name"],
        "picture": payload["picture"],
    }
