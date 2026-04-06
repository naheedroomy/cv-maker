"""SQLite database module — init, schema, and connection helpers.

All connections set PRAGMA busy_timeout=5000. WAL mode is set on init
and persists in the database file. Write transactions must use
BEGIN IMMEDIATE (not BEGIN DEFERRED) — see Phase 5 RESEARCH.md Pitfall 1.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path(os.environ.get("CV_MAKER_DB_PATH", "backend/cv_maker.db"))

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS jobs (
    id               TEXT PRIMARY KEY,
    company_name     TEXT NOT NULL,
    job_link         TEXT,
    job_text         TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending',
    tailored_cv_json TEXT,
    gap_diff_json    TEXT,
    pdf_path         TEXT,
    model            TEXT NOT NULL DEFAULT 'claude-haiku',
    creativity_level INTEGER NOT NULL DEFAULT 2,
    applied          INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


async def init_db(db_path: Path | None = None) -> None:
    """Create database file, enable WAL mode, and create tables.

    Args:
        db_path: Override path for testing. Defaults to DB_PATH.
    """
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.executescript(_SCHEMA)
        # Idempotent migration: add model column if absent
        cursor = await db.execute("PRAGMA table_info(jobs)")
        columns = {row[1] async for row in cursor}
        if "model" not in columns:
            await db.execute(
                "ALTER TABLE jobs ADD COLUMN model TEXT NOT NULL DEFAULT 'claude-haiku'"
            )
            logger.info("Migration: added 'model' column to jobs table")
        if "applied" not in columns:
            await db.execute(
                "ALTER TABLE jobs ADD COLUMN applied INTEGER NOT NULL DEFAULT 0"
            )
            logger.info("Migration: added 'applied' column to jobs table")
        if "creativity_level" not in columns:
            await db.execute(
                "ALTER TABLE jobs ADD COLUMN creativity_level INTEGER NOT NULL DEFAULT 2"
            )
            logger.info("Migration: added 'creativity_level' column to jobs table")
        await db.commit()
    logger.info("Database initialized at %s", path)


async def get_db(db_path: Path | None = None) -> aiosqlite.Connection:
    """Open a connection with WAL and busy_timeout=5000 set.

    Caller is responsible for closing the connection (use `async with` or `await db.close()`).

    Args:
        db_path: Override path for testing. Defaults to DB_PATH.
    """
    path = db_path or DB_PATH
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    return db
