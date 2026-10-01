# tests/test_db.py
"""Tests for backend/db.py — SQLite initialization and connection helpers."""
from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite


def test_init_db_creates_file(tmp_path: Path) -> None:
    """init_db() creates the database file at the specified path."""
    from backend.db import init_db

    db_path = tmp_path / "test.db"
    assert not db_path.exists()
    asyncio.run(init_db(db_path=db_path))
    assert db_path.exists()


def test_init_db_wal_mode(tmp_path: Path) -> None:
    """After init_db(), the database has WAL journal mode enabled."""
    from backend.db import init_db

    db_path = tmp_path / "test.db"
    asyncio.run(init_db(db_path=db_path))

    async def check_wal() -> str:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            return row[0]

    mode = asyncio.run(check_wal())
    assert mode == "wal"


def test_init_db_jobs_table_columns(tmp_path: Path) -> None:
    """After init_db(), the jobs table has all expected columns."""
    from backend.db import init_db

    db_path = tmp_path / "test.db"
    asyncio.run(init_db(db_path=db_path))

    expected_columns = {
        "id",
        "user_id",
        "company_name",
        "job_link",
        "job_text",
        "status",
        "tailored_cv_json",
        "gap_diff_json",
        "pdf_path",
        "created_at",
        "updated_at",
        "model",
        "applied",
        "applied_at",
        "creativity_level",
        "cover_letter_text",
        "cover_letter_notes",
        "cover_letter_model",
        "cover_letter_tone",
        "cv_history_json",
        "cl_history_json",
        "user_notes",
        "model_id",
        "reasoning_effort",
        "base_cv_id",
        "base_cv_name",
    }

    async def get_columns() -> set[str]:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("PRAGMA table_info(jobs)")
            rows = await cursor.fetchall()
            return {row[1] for row in rows}

    columns = asyncio.run(get_columns())
    assert columns == expected_columns


def test_get_db_busy_timeout(tmp_path: Path) -> None:
    """get_db() returns a connection with busy_timeout=5000."""
    from backend.db import get_db, init_db

    db_path = tmp_path / "test.db"
    asyncio.run(init_db(db_path=db_path))

    async def check_timeout() -> int:
        db = await get_db(db_path=db_path)
        try:
            cursor = await db.execute("PRAGMA busy_timeout")
            row = await cursor.fetchone()
            return row[0]
        finally:
            await db.close()

    timeout = asyncio.run(check_timeout())
    assert timeout == 5000


def test_get_db_row_factory(tmp_path: Path) -> None:
    """get_db() returns a connection with row_factory set to aiosqlite.Row."""
    from backend.db import get_db, init_db

    db_path = tmp_path / "test.db"
    asyncio.run(init_db(db_path=db_path))

    async def check_row_factory() -> bool:
        db = await get_db(db_path=db_path)
        try:
            return db.row_factory is aiosqlite.Row
        finally:
            await db.close()

    result = asyncio.run(check_row_factory())
    assert result is True


def test_init_db_idempotent(tmp_path: Path) -> None:
    """Calling init_db() twice does not raise an error (CREATE TABLE IF NOT EXISTS)."""
    from backend.db import init_db

    db_path = tmp_path / "test.db"
    asyncio.run(init_db(db_path=db_path))
    # Second call must not raise
    asyncio.run(init_db(db_path=db_path))


async def test_base_cvs_schema_and_migration(tmp_path: Path):
    from backend.db import get_db, init_db

    test_db = tmp_path / "test.db"
    await init_db(test_db)
    db = await get_db(test_db)
    try:
        # Check base_cvs table exists
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='base_cvs'"
        )
        row = await cursor.fetchone()
        assert row is not None

        # Check default seeded CV for user 1
        cursor = await db.execute("SELECT * FROM base_cvs WHERE user_id = 1")
        cv_rows = await cursor.fetchall()
        assert len(cv_rows) == 1
        assert cv_rows[0]["name"] == "Main Base CV"
        assert cv_rows[0]["is_default"] == 1

        # Check jobs table columns
        cursor = await db.execute("PRAGMA table_info(jobs)")
        cols = {r["name"] for r in await cursor.fetchall()}
        assert "base_cv_id" in cols
        assert "base_cv_name" in cols
    finally:
        await db.close()


async def test_base_cvs_table_created(tmp_path: Path):
    """init_db() creates base_cvs table and adds base_cv_id, base_cv_name to jobs."""
    from backend.db import get_db, init_db

    test_db = tmp_path / "test.db"
    await init_db(test_db)
    db = await get_db(test_db)
    try:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='base_cvs'"
        )
        assert await cursor.fetchone() is not None

        cursor = await db.execute("PRAGMA table_info(jobs)")
        cols = {r["name"] for r in await cursor.fetchall()}
        assert "base_cv_id" in cols
        assert "base_cv_name" in cols
    finally:
        await db.close()


async def test_base_cvs_migrates_existing_user_cv(tmp_path: Path):
    """When a user has base_cv_yaml, init_db() creates a default entry in base_cvs."""
    from backend.db import get_db, init_db

    test_db = tmp_path / "test.db"
    # Pre-populate database with an existing user having base_cv_yaml
    async with aiosqlite.connect(test_db) as db:
        await db.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, google_id TEXT, "
            "email TEXT, name TEXT, created_at TEXT, base_cv_yaml TEXT)"
        )
        await db.execute(
            "CREATE TABLE jobs (id TEXT PRIMARY KEY, user_id INTEGER, company_name TEXT, "
            "job_text TEXT, status TEXT, created_at TEXT, updated_at TEXT)"
        )
        user_yaml = "contact:\n  name: Existing User\n"
        await db.execute(
            "INSERT INTO users (id, google_id, email, name, created_at, base_cv_yaml) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (2, "user2", "user2@example.com", "User Two", "2026-01-01T00:00:00", user_yaml),
        )
        await db.commit()

    # Run init_db to migrate
    await init_db(test_db)

    db = await get_db(test_db)
    try:
        cursor = await db.execute("SELECT * FROM base_cvs WHERE user_id = 2")
        cv_rows = await cursor.fetchall()
        assert len(cv_rows) == 1
        assert cv_rows[0]["name"] == "Main Base CV"
        assert cv_rows[0]["is_default"] == 1
        assert cv_rows[0]["cv_yaml"] == "contact:\n  name: Existing User\n"
        assert cv_rows[0]["id"] is not None
    finally:
        await db.close()


async def test_base_cvs_seeds_from_yaml_if_empty(tmp_path: Path, monkeypatch):
    """When a user has no CV, init_db() seeds from data/base_cv.yaml as 'Main Base CV'."""
    from backend.db import get_db, init_db

    test_yaml = tmp_path / "seed_cv.yaml"
    test_yaml.write_text("contact:\n  name: Seeded User\n", encoding="utf-8")
    monkeypatch.setenv("BASE_CV_PATH", str(test_yaml))

    test_db = tmp_path / "test.db"
    await init_db(test_db)

    db = await get_db(test_db)
    try:
        cursor = await db.execute("SELECT * FROM base_cvs WHERE user_id = 1")
        cv_rows = await cursor.fetchall()
        assert len(cv_rows) == 1
        assert cv_rows[0]["name"] == "Main Base CV"
        assert cv_rows[0]["is_default"] == 1
        assert cv_rows[0]["cv_yaml"] == "contact:\n  name: Seeded User\n"
    finally:
        await db.close()

