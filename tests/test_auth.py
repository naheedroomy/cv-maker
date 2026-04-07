"""Unit tests for backend/auth.py — JWT create/decode and get_current_user.

Tests follow TDD pattern:
- Tests 1-3: JWT roundtrip and validation
- Tests 4-6: get_current_user dependency (valid bearer, dev-mode fallback, production mode)
"""
from __future__ import annotations

import time

import pytest

from backend.auth import create_jwt, decode_jwt, get_current_user
from backend.db import ANONYMOUS_USER_ID


def test_jwt_roundtrip():
    """Test 1: create_jwt produces a token that decode_jwt can decode back to the same claims."""
    token = create_jwt(user_id=42, email="alice@example.com", name="Alice Smith", picture="https://example.com/pic.jpg")
    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_jwt(token)
    assert payload["user_id"] == 42
    assert payload["email"] == "alice@example.com"
    assert payload["name"] == "Alice Smith"
    assert payload["picture"] == "https://example.com/pic.jpg"


def test_decode_jwt_expired_token():
    """Test 2: decode_jwt raises ValueError for an expired token."""
    import jwt as pyjwt
    from datetime import datetime, timezone, timedelta

    expired_payload = {
        "user_id": 1,
        "email": "test@example.com",
        "name": "Test User",
        "picture": "",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    expired_token = pyjwt.encode(expired_payload, "dev-secret-change-me", algorithm="HS256")

    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_jwt(expired_token)


def test_decode_jwt_wrong_secret():
    """Test 3: decode_jwt raises ValueError for a token signed with the wrong secret."""
    import jwt as pyjwt
    from datetime import datetime, timezone, timedelta

    payload = {
        "user_id": 1,
        "email": "test@example.com",
        "name": "Test User",
        "picture": "",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    wrong_secret_token = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")

    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_jwt(wrong_secret_token)


@pytest.mark.asyncio
async def test_get_current_user_valid_bearer(monkeypatch):
    """Test 4: get_current_user with a valid Bearer token returns user dict with 'id' key."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-tests")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    token = create_jwt(user_id=99, email="bob@example.com", name="Bob Jones", picture="")
    authorization = f"Bearer {token}"

    user = await get_current_user(authorization=authorization)
    assert user["id"] == 99
    assert user["email"] == "bob@example.com"
    assert user["name"] == "Bob Jones"
    assert "picture" in user


@pytest.mark.asyncio
async def test_get_current_user_dev_mode_fallback(monkeypatch):
    """Test 5: get_current_user without Authorization header returns ANONYMOUS_USER_ID when GOOGLE_CLIENT_ID is not set (dev-mode fallback per D-02)."""
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    user = await get_current_user(authorization=None)
    assert user["id"] == ANONYMOUS_USER_ID
    assert user["email"] == "local@localhost"
    assert user["name"] == "Local User"


@pytest.mark.asyncio
async def test_get_current_user_production_mode_raises_401(monkeypatch):
    """Test 6: get_current_user without Authorization header raises HTTPException 401 when GOOGLE_CLIENT_ID IS set (production mode)."""
    from fastapi import HTTPException

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "some-client-id.apps.googleusercontent.com")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=None)

    assert exc_info.value.status_code == 401
    assert "Not authenticated" in exc_info.value.detail
