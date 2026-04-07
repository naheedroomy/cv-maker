---
phase: 1004-cv-ingestion-and-visual-editor
plan: "03"
subsystem: backend+frontend
tags: [cv-pipeline, worker, sidebar, db-first, auth]
dependency_graph:
  requires:
    - 1004-01 (backend/routers/cv.py — GET /cv/me endpoint + users.base_cv_yaml schema)
    - 1003 (backend/auth.py — get_current_user, JWT; frontend apiFetch utility)
  provides:
    - backend/worker.py::job_worker (user_id param, DB-first CV loading)
    - frontend/src/components/AppSidebar.vue (CV status from /api/cv/me)
  affects:
    - backend/routers/jobs.py (passes user_id to job_worker)
tech_stack:
  added: []
  patterns:
    - DB-first resource loading with YAML file fallback in background worker
    - apiFetch (auth-aware) for sidebar CV status polling
key_files:
  created: []
  modified:
    - backend/worker.py
    - backend/routers/jobs.py
    - frontend/src/components/AppSidebar.vue
decisions:
  - "user_id defaults to 1 (ANONYMOUS_USER_ID) in job_worker for backward compat"
  - "DB query uses a fresh connection (get_db + finally close) per existing worker pattern"
  - "Sidebar fetchCvInfo uses apiFetch (not plain fetch) to carry JWT Bearer token"
  - "Empty CV state text changed from 'No CV imported' to 'No CV uploaded' for clarity"
metrics:
  duration: 166s
  completed: "2026-04-07"
  tasks_completed: 2
  files_modified: 3
---

# Phase 1004 Plan 03: Pipeline Integration & Sidebar Status — Summary

**One-liner:** DB-first CV loading in the job worker (query users.base_cv_yaml, fall back to YAML file) with sidebar CV status wired to the auth-protected /api/cv/me endpoint.

## What Was Built

### Task 1: Worker loads CV from DB first, falls back to YAML file

Modified `backend/worker.py`:
- Added `user_id: int = 1` parameter to `job_worker()` (default=1 for backward compat)
- Added `import yaml` and `from core.models import BaseCV` to imports
- Replaced the single `asyncio.to_thread(load_base_cv)` call with a DB-first load:
  1. Opens a fresh DB connection, executes `SELECT base_cv_yaml FROM users WHERE id=?`
  2. If row has YAML: `yaml.safe_load()` + `BaseCV.model_validate()` + logs "loaded from DB"
  3. Connection closed in `finally` block
  4. If `base_cv is None`: falls back to `asyncio.to_thread(load_base_cv)` + logs "loaded from YAML file"

Modified `backend/routers/jobs.py`:
- `create_job` already has `user: dict = Depends(get_current_user)` (from phase 1003)
- Added `user_id=user["id"]` to the `job_worker(...)` call in `schedule_background_task`

### Task 2: Sidebar CV status uses /api/cv/me endpoint

Modified `frontend/src/components/AppSidebar.vue`:
- `fetchCvInfo()` now calls `/api/cv/me` via `apiFetch` (auto-injects Bearer token)
- Parses `{ has_cv: boolean, cv: BaseCV | null }` response from the new endpoint
- When `has_cv=true`: populates `cvInfo` with `name`, `roles` (experience.length), `skills` (skills.length), `certifications` (certifications.length)
- When `has_cv=false`: sets `cvInfo = { loaded: false }`
- Empty CV state: changed link text from "Import CV" to "Upload CV" and destination from `/convert` to `/base-cv`

### Task 3: End-to-end verification (checkpoint:human-verify)

Human verification required. Steps to verify:

1. Start backend: `uv run uvicorn backend.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Sign in (or use dev mode without auth)
4. Navigate to /base-cv — should see upload zone and "Create CV from scratch" button
5. Upload a PDF CV — should see parsing progress, then editor populates with parsed data
6. Verify all sections are present: Contact, Summary, Work Experience, Education, Skills, Certifications, Projects
7. Edit a field (e.g., change your name), click "Save CV"
8. Reload the page — the edit should persist
9. Check sidebar — should show your name, role/skill/cert counts
10. Submit a tailoring job — the pipeline should use your uploaded CV (check backend logs for "Base CV loaded from DB")
11. Try "Remove CV" — confirms, then shows upload zone again
12. Try "Create CV from scratch" — shows empty editor sections

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Merge Required (Infrastructure)

The worktree `worktree-agent-a4a1eaf4` had diverged from `gsd/v3.0-deploy-auth-cv-editor` and was missing plan 01/1003 files (`backend/routers/cv.py`, `backend/auth.py`, `frontend/src/utils/apiFetch.ts`, etc.). A fast-forward merge was performed before starting task execution. This is not a code deviation — the worktree was simply behind the main development branch.

## Known Stubs

None — all code paths are fully wired:
- Worker queries real DB for user's CV YAML
- Sidebar calls real auth-protected endpoint via apiFetch
- Empty state correctly links to the visual editor at /base-cv

## Checkpoint: Human Verification Required

**Type:** human-verify  
**What was automated:** Both code tasks (worker DB-first loading + sidebar endpoint update) are committed.  
**What needs human verification:** End-to-end flow as described in Task 3 above (12 manual steps covering PDF upload, parse, edit, save, pipeline use, sidebar status).

## Self-Check: PASSED

- `backend/worker.py` modified — FOUND (commit c005f18)
- `backend/routers/jobs.py` modified — FOUND (commit c005f18)
- `frontend/src/components/AppSidebar.vue` modified — FOUND (commit d4f68c6)
- Commit `c005f18` (Task 1) — present in `git log --oneline worktree-agent-a4a1eaf4`
- Commit `d4f68c6` (Task 2) — present in `git log --oneline worktree-agent-a4a1eaf4`
- Worker signature verification: `user_id` in `sig.parameters` — PASSED (verified via `uv run python -c`)
- vue-tsc type check — PASSED (no type errors)
