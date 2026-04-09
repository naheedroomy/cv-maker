"""SQLite database module — init, schema, and connection helpers.

Multi-tenant schema: users table with user_id FK on jobs and settings.
All connections set PRAGMA busy_timeout=5000 and PRAGMA foreign_keys=ON.
WAL mode is set on init and persists in the database file.
Write transactions must use BEGIN IMMEDIATE (not BEGIN DEFERRED) —
see Phase 5 RESEARCH.md Pitfall 1.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path(os.environ.get("CV_MAKER_DB_PATH", "backend/cv_maker.db"))

ANONYMOUS_USER_ID: int = 1

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    google_id     TEXT UNIQUE,
    email         TEXT,
    name          TEXT,
    created_at    TEXT NOT NULL,
    base_cv_yaml  TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    id               TEXT PRIMARY KEY,
    user_id          INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
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
    applied_at       TEXT,
    cover_letter_text TEXT,
    cover_letter_notes TEXT,
    cover_letter_model TEXT,
    cover_letter_tone TEXT,
    cv_history_json  TEXT,
    cl_history_json  TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    user_id  INTEGER NOT NULL REFERENCES users(id),
    key      TEXT NOT NULL,
    value    TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);

CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id);
"""


async def init_db(db_path: Path | None = None) -> None:
    """Create database file, enable WAL mode, and create tables.

    On first run after multi-tenant migration, performs a clean-slate
    migration: deletes the pre-multi-tenant DB file and recreates fresh.
    Seeds a placeholder local user (id=1) for anonymous access.

    Args:
        db_path: Override path for testing. Defaults to DB_PATH.
    """
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    # Clean-slate migration: if DB exists but has no users table, delete it
    if path.exists():
        async with aiosqlite.connect(path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            has_users = await cursor.fetchone()
        if not has_users:
            path.unlink()
            logger.info(
                "Clean-slate migration: deleted pre-multi-tenant DB at %s", path
            )

    # Create tables with multi-tenant schema
    async with aiosqlite.connect(path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(_SCHEMA)

        # Migrate: add cover_letter_model and cover_letter_tone columns if missing
        cursor = await db.execute("PRAGMA table_info(jobs)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "cover_letter_model" not in columns:
            await db.execute("ALTER TABLE jobs ADD COLUMN cover_letter_model TEXT")
        if "cover_letter_tone" not in columns:
            await db.execute("ALTER TABLE jobs ADD COLUMN cover_letter_tone TEXT")
        if "cv_history_json" not in columns:
            await db.execute("ALTER TABLE jobs ADD COLUMN cv_history_json TEXT")
        if "cl_history_json" not in columns:
            await db.execute("ALTER TABLE jobs ADD COLUMN cl_history_json TEXT")
        if "applied_at" not in columns:
            await db.execute("ALTER TABLE jobs ADD COLUMN applied_at TEXT")

        # Seed placeholder local user (idempotent)
        await db.execute(
            "INSERT OR IGNORE INTO users (id, google_id, email, name, created_at) "
            "VALUES (?, 'local', 'local@localhost', 'Local User', ?)",
            (ANONYMOUS_USER_ID, datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()

    logger.info("Database initialized at %s", path)


async def get_db(db_path: Path | None = None) -> aiosqlite.Connection:
    """Open a connection with WAL, busy_timeout=5000, and foreign_keys=ON.

    Caller is responsible for closing the connection (use `async with` or
    `await db.close()`).

    Args:
        db_path: Override path for testing. Defaults to DB_PATH.
    """
    path = db_path or DB_PATH
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.execute("PRAGMA foreign_keys=ON")
    return db
