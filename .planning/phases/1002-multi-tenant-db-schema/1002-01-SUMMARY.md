---
phase: 1002-multi-tenant-db-schema
plan: 01
subsystem: database
tags: [sqlite, multi-tenant, schema, migration, aiosqlite]

requires:
  - phase: none
    provides: greenfield DB schema rewrite
provides:
  - users table with google_id, email, name, base_cv_yaml
  - user_id FK on jobs and settings tables
  - ANONYMOUS_USER_ID constant for pre-auth user scoping
  - clean-slate migration logic
  - PRAGMA foreign_keys=ON enforcement
affects: [1002-02, 1002-03, 1003-google-auth]

tech-stack:
  added: []
  patterns: [clean-slate migration, ANONYMOUS_USER_ID sentinel, composite PK settings]

key-files:
  created: []
  modified: [backend/db.py]

key-decisions:
  - "Clean-slate migration deletes pre-multi-tenant DB — no data preservation needed at this milestone boundary"
  - "ANONYMOUS_USER_ID=1 in db.py as grep-able sentinel for Phase 1003 JWT replacement"

patterns-established:
  - "PRAGMA foreign_keys=ON in every connection (init_db + get_db)"
  - "Placeholder local user seeded idempotently at init_db time"

requirements-completed: [TENANT-01, TENANT-02, TENANT-03, TENANT-04, TENANT-05]

duration: 1min
completed: 2026-04-07
---

# Phase 1002 Plan 01: DB Schema Summary

**Multi-tenant SQLite schema with users table, user_id FKs on jobs/settings, clean-slate migration, and ANONYMOUS_USER_ID sentinel constant**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-07T14:58:06Z
- **Completed:** 2026-04-07T14:59:05Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Rewrote `backend/db.py` with complete multi-tenant schema: `users`, `jobs` (with `user_id` FK), `settings` (with composite PK `(user_id, key)`)
- Implemented clean-slate migration that detects and deletes pre-multi-tenant DB files on startup
- Added `ANONYMOUS_USER_ID = 1` constant and placeholder local user seeding
- Enabled `PRAGMA foreign_keys=ON` in both `init_db()` and `get_db()`
- Removed all legacy `PRAGMA table_info` migration blocks — columns are now in base schema

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite _SCHEMA, init_db(), and get_db() for multi-tenant DB** - `b5ccb36` (feat)

## Files Created/Modified
- `backend/db.py` - Complete rewrite: multi-tenant schema, clean-slate migration, FK enforcement, placeholder user seeding

## Decisions Made
- Followed plan exactly — clean-slate migration strategy per D-01, users table per D-02, jobs FK per D-03, settings composite PK per D-04
- ANONYMOUS_USER_ID placed in db.py as recommended by D-09

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for 1002-02 (settings cache rewrite) — `ANONYMOUS_USER_ID` constant is now available for import
- `get_db()` now enforces foreign keys — all existing queries will work but FK violations will be caught
- Clean-slate migration means the old DB file will be deleted on next server start

---
*Phase: 1002-multi-tenant-db-schema*
*Completed: 2026-04-07*
