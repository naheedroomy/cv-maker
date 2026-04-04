---
phase: 04-streamlit-ui
plan: "02"
subsystem: ui
tags: [streamlit, ui, history, persistence, session-state, sidebar]
one_liner: "History persistence to ~/.cv-maker/history/ with sidebar browser for past runs, restoring results without re-invoking the pipeline"
dependency_graph:
  requires:
    - 04-01  # app.py base UI with session_state pattern
    - 01-01  # TailoredCV, GapItem models (model_dump/model_validate)
  provides:
    - _save_history() — persists completed runs as timestamped JSON
    - _load_history_index() — loads history newest-first, skipping corrupt files
    - Sidebar selectbox — browse and restore past runs without re-invoking Claude CLI
  affects:
    - app.py — targeted additions only; no existing logic modified
tech_stack:
  added:
    - json (stdlib) — serialise/deserialise history records
    - datetime (stdlib) — generate ISO timestamps for filenames
  patterns:
    - Timestamped slug filename: "{YYYYMMDDTHHMMSS}-{role-slug}.json"
    - model_dump() / model_validate() round-trip for Pydantic serialisation
    - Sidebar on_change callback populates session_state without re-running pipeline
    - pdf_bytes intentionally excluded from history (not serialisable; absent for restored runs)
key_files:
  created: []
  modified:
    - app.py  # Added _save_history(), _load_history_index(), sidebar history browser, _save_history() call in generate block
decisions:
  - "pdf_bytes excluded from history JSON — PDF bytes are large and require a running LaTeX environment to re-generate; restored runs simply omit the Download PDF button"
  - "role_label derived from first line of job_text (truncated to 40 chars) — provides a human-readable label without requiring extra user input"
  - "Corrupt JSON files silently skipped in _load_history_index() — a single corrupt history file should not block the sidebar from loading valid entries"
  - "checkpoint:human-verify auto-approved in autonomous mode — code structure verified statically; smoke test instructions documented for manual execution"
metrics:
  duration_minutes: 1
  completed_date: "2026-04-04"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 1
---

# Phase 04 Plan 02: History Persistence and Sidebar Summary

History persistence to `~/.cv-maker/history/` with sidebar browser for past runs, restoring results without re-invoking the pipeline.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add history save/load and sidebar to app.py | b3ad892 | app.py |
| 2 | Human smoke test — full end-to-end flow (auto-approved) | — | — |

## What Was Built

Three targeted additions to `app.py` completing requirements HIST-01 and HIST-02:

### `_save_history()`

Persists a completed run to `~/.cv-maker/history/` as a timestamped JSON file. The filename format is `{YYYYMMDDTHHMMSS}-{role-slug}.json` where the slug is derived from the first 40 characters of the role title, with non-alphanumeric characters replaced by `-`. The JSON record contains: `timestamp`, `role_title`, `job_text`, `tailored_cv` (via `model_dump()`), and `gap_diff` (list of `model_dump()` outputs). Called immediately after `pdf_bytes` is stored in session_state — only on successful generation.

### `_load_history_index()`

Scans `~/.cv-maker/history/` for `*.json` files, sorts them newest-first by filename (lexicographic sort of ISO timestamps is correct), and returns a list of dicts with `path`, `label`, and `data` keys. Corrupt or malformed JSON files are silently skipped via `json.JSONDecodeError` / `KeyError` except handler.

### Sidebar history browser

Added before `st.title()` using a `with st.sidebar:` block. On first launch (no history), displays "No past runs yet." When history exists, shows a `st.selectbox` with `"(current run)"` as the first option followed by all past run labels. The `_on_history_change()` callback uses `model_validate()` to restore `TailoredCV` and `list[GapItem]` from the chosen JSON record into `st.session_state["result"]`, and sets `st.session_state["pdf_bytes"] = None` (Download PDF button intentionally absent for restored runs).

### Role label extraction

In the generate block, `role_label` is derived from the first non-empty line of `job_text` (truncated to 40 chars), providing a human-readable sidebar label without requiring additional user input.

## Checkpoint: Task 2 — Human Smoke Test

**Status:** Auto-approved (autonomous mode)

**What to verify manually:**

Run `uv run streamlit run app.py` and execute the 13-step checklist from the plan:

1. App loads — title visible, text area and Generate button present
2. Sidebar shows "No past runs yet." on first launch
3. Paste a job listing and click Generate
4. Spinner appears with elapsed time (30-90 seconds)
5. Gap table, CV preview, and Download PDF button appear after generation
6. PDF downloads and opens as a valid CV
7. Interacting with widgets does not re-trigger the pipeline
8. Browser refresh resets session_state (expected)
9. Generate again; sidebar now shows one past run
10. Select the past run — gap table and preview restore without spinner
11. Download PDF button is absent for restored history run

## Decisions Made

- **pdf_bytes excluded from history**: PDF bytes are large, not JSON-serialisable, and require a running LaTeX/latexmk installation to re-generate. Omitting them from history and clearing `pdf_bytes` on restore is the correct trade-off. The absence of the Download PDF button signals to the user they need to re-generate to get a fresh PDF.
- **Silent skip on corrupt files**: `_load_history_index()` continues past corrupt files rather than raising. A single malformed file (e.g., from an interrupted write) should not prevent the sidebar from loading.
- **Auto-approved checkpoint**: The code was verified structurally (ruff passes, syntax valid, all acceptance criteria grep patterns confirmed). The interactive smoke test requires a running Streamlit server and cannot be automated.

## Deviations from Plan

### Auto-approved checkpoint

**Task 2 — checkpoint:human-verify**
- **Reason:** Execution objective specified autonomous mode; checkpoint auto-approved after verifying Task 1 code structure meets all acceptance criteria.
- **Impact:** Interactive smoke test (13-step checklist) was not executed by the agent.
- **Action required:** Run `uv run streamlit run app.py` and execute the checklist from `.planning/phases/04-streamlit-ui/04-02-PLAN.md` Task 2 before considering Phase 04 complete.

## Known Stubs

None. History save is fully wired: generate block calls `_save_history()` → writes to disk. Sidebar calls `_load_history_index()` → reads from disk → populates `st.session_state`. All data flows are connected.

## Self-Check: PASSED

- FOUND: app.py (modified)
- FOUND: _save_history function in app.py (line 29)
- FOUND: _load_history_index function in app.py (line 47)
- FOUND: with st.sidebar: block in app.py (line 150)
- FOUND: st.selectbox in sidebar in app.py (line 169)
- FOUND: _save_history call in generate block in app.py (line 201)
- FOUND: commit b3ad892
- ruff check: PASSED
- syntax parse: PASSED
