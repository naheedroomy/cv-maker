"""Integration tests for backend/main.py — FastAPI app entry point.

Tests cover:
1. GET /api/ returns 200 with {"status": "ok"}
2. GET /api/ response has Content-Type application/json
3. CORS preflight from http://localhost:5173 returns Access-Control-Allow-Origin
4. CORS preflight from http://evil.com:9999 does NOT return matching ACAO header
5. App startup calls init_db via lifespan
6. schedule_background_task returns asyncio.Task and stores it in registry
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from starlette.testclient import TestClient

from backend.main import _background_tasks, app, schedule_background_task


def test_health_check_status_code():
    """GET /api/ returns 200."""
    with TestClient(app) as client:
        response = client.get("/api/")
        assert response.status_code == 200


def test_health_check_json_body():
    """GET /api/ returns JSON body containing status ok."""
    with TestClient(app) as client:
        response = client.get("/api/")
        data = response.json()
        assert data["status"] == "ok"


def test_health_check_content_type():
    """GET /api/ response has Content-Type application/json."""
    with TestClient(app) as client:
        response = client.get("/api/")
        assert "application/json" in response.headers.get("content-type", "")


def test_cors_allows_vue_dev_server():
    """CORS preflight from http://localhost:5173 returns correct ACAO header."""
    with TestClient(app) as client:
        response = client.options(
            "/api/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_blocks_unknown_origin():
    """CORS preflight from http://evil.com:9999 does NOT return matching ACAO header."""
    with TestClient(app) as client:
        response = client.options(
            "/api/",
            headers={
                "Origin": "http://evil.com:9999",
                "Access-Control-Request-Method": "GET",
            },
        )
        acao = response.headers.get("access-control-allow-origin", "")
        assert acao != "http://evil.com:9999"


def test_lifespan_calls_init_db():
    """App startup calls init_db during lifespan."""
    with patch("backend.main.init_db", new_callable=AsyncMock) as mock_init_db:
        with TestClient(app):
            mock_init_db.assert_called_once()


def test_schedule_background_task():
    """schedule_background_task returns asyncio.Task and stores it in registry."""

    async def _test():
        async def dummy():
            return 42

        task = schedule_background_task(dummy())
        assert isinstance(task, asyncio.Task)
        assert task in _background_tasks
        result = await task
        assert result == 42
        # After completion, done callback removes it from the set
        await asyncio.sleep(0)  # Let callback fire
        assert task not in _background_tasks

    asyncio.run(_test())
