"""Application title preference persists through the API and is isolated per user."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

from fastapi import FastAPI
from starlette.testclient import TestClient

from backend.auth import get_current_user
from backend.db import get_db, init_db
from backend.routers.settings import router
from backend.settings_cache import get_setting


def test_application_title_preference(tmp_path):
    db_path = tmp_path / "settings.db"

    async def prepare():
        await init_db(db_path)
        db = await get_db(db_path)
        try:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute(
                "INSERT INTO users (id, email, name, created_at) VALUES (2, ?, ?, ?)",
                ("other@example.com", "Other", "2026-10-09T00:00:00"),
            )
            await db.commit()
        finally:
            await db.close()

    asyncio.run(prepare())
    user = {"id": 1}
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: user

    with patch("backend.db.DB_PATH", db_path), TestClient(app) as client:
        assert client.get("/api/settings").json()["ai_application_titles"] is True
        res = client.put("/api/settings", json={"ai_application_titles": False})
        assert res.status_code == 200
        assert res.json()["ai_application_titles"] is False
        assert client.get("/api/settings").json()["ai_application_titles"] is False
        assert asyncio.run(get_setting("ai_application_titles", 1)) == "false"

        # Partial saves must not reset the preference.
        client.put("/api/settings", json={"cv_filename": "My-CV"})
        assert client.get("/api/settings").json()["ai_application_titles"] is False

        user["id"] = 2
        assert client.get("/api/settings").json()["ai_application_titles"] is True
        assert asyncio.run(get_setting("ai_application_titles", 2)) == "true"
        user["id"] = 1
        assert client.put("/api/settings", json={"ai_application_titles": True}).json()[
            "ai_application_titles"
        ] is True
        assert asyncio.run(get_setting("ai_application_titles", 1)) == "true"
