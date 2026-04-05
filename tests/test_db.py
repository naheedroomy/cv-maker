# tests/test_db.py
"""Tests for backend/db.py — SQLite initialization and connection helpers."""
from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite
import pytest


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
    """After init_db(), the jobs table has all 11 expected columns."""
    from backend.db import init_db

    db_path = tmp_path / "test.db"
    asyncio.run(init_db(db_path=db_path))

    expected_columns = {
        "id",
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
