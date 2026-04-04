---
phase: 04-streamlit-ui
plan: "01"
subsystem: ui
tags: [streamlit, ui, pandas, session-state, pdf-download]
one_liner: "Single-page Streamlit UI with session_state-guarded pipeline call, color-coded gap table, CV preview, and PDF download"
dependency_graph:
  requires:
    - 03-03  # run_pipeline() public API
    - 02-01  # render_latex(), render_pdf()
    - 01-01  # load_base_cv(), BaseCV, TailoredCV, GapItem
  provides:
    - UI entry point via `streamlit run app.py`
    - Color-coded gap analysis table (green=present, red=missing)
    - Tailored CV preview with all sections
    - PDF download button
  affects:
    - End-to-end user workflow — this is the only user-facing surface
tech_stack:
  added:
    - streamlit 1.56.0 — full UI framework
    - pandas 3.0.2 — DataFrame for gap table with style.apply coloring
  patterns:
    - st.session_state guard: pipeline called only inside if st.button() block
    - st.cache_data for base CV load — persists across reruns
    - Results read exclusively from session_state — no recomputation on widget interaction
key_files:
  created:
    - app.py  # Single-page Streamlit UI — full pipeline integration
  modified:
    - pyproject.toml  # Added streamlit>=1.45.0 and pandas>=2.2
    - uv.lock         # Updated with 31 new packages
decisions:
  - "session_state used for both result and pdf_bytes — prevents re-running expensive pipeline on every Streamlit rerun"
  - "st.cache_data on _load_cv() — base CV loaded once, cached across all reruns"
  - "pandas DataFrame with style.apply for gap table coloring — clean, idiomatic approach"
  - "st.stop() follows st.error() in _load_cv() — stops further execution if base CV is missing or invalid"
metrics:
  duration_minutes: 1
  completed_date: "2026-04-04"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
---

# Phase 04 Plan 01: Streamlit UI Summary

Single-page Streamlit UI with session_state-guarded pipeline call, color-coded gap table, CV preview, and PDF download.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add streamlit and pandas to pyproject.toml | c9bc6a1 | pyproject.toml, uv.lock |
| 2 | Implement app.py — Streamlit UI | 451212a | app.py |

## What Was Built

`app.py` is the sole new source file — a single-page Streamlit application that:

1. **Loads the base CV once** via `@st.cache_data` — persists across all reruns. On `FileNotFoundError` or `RuntimeError` it surfaces the message and calls `st.stop()`.

2. **Session state initialisation** at module level (before any widgets): `st.session_state["result"]` and `st.session_state["pdf_bytes"]` both default to `None`.

3. **Generate button guard**: `run_pipeline()` and `render_pdf()` are called ONLY inside the `if st.button("Generate Tailored CV"):` block. Results are stored to session_state immediately. Widget interactions (scrolling, typing) never re-trigger the pipeline.

4. **Gap analysis table**: `_render_gap_table()` builds a pandas DataFrame and applies `style.apply(_color_row, axis=1)` for green (#d4edda) / red (#f8d7da) row coloring based on `GapItem.present`.

5. **CV preview**: `_render_cv_preview()` renders all TailoredCV fields as formatted markdown — summary, experience with bullets and technologies, skills, highlighted technologies, education, certifications.

6. **PDF download**: `st.download_button` reads bytes from `st.session_state["pdf_bytes"]` with `mime="application/pdf"`. Filename includes the candidate name.

All ruff lint rules pass (`E`, `F`, `I`, `S`). `st.set_page_config()` is the first Streamlit call.

## Decisions Made

- **session_state guard pattern**: The plan specified this explicitly. `run_pipeline()` is expensive (30-90s). Without session_state, every Streamlit rerun (triggered by any widget interaction) would re-call the pipeline. Storing result in `st.session_state["result"]` means the results section reads from cache, not from re-execution.
- **st.cache_data on _load_cv()**: The base CV doesn't change during a session. Caching avoids re-reading and re-validating the YAML on every rerun.
- **pandas style.apply for coloring**: Simple and idiomatic for Streamlit DataFrames. The alternative (custom HTML/CSS) would be more fragile and harder to maintain.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The UI is fully wired to the backend pipeline. All data flows from `run_pipeline()` → `st.session_state["result"]` → render helpers.

Note: The app requires `base_cv.yaml` to exist at the working directory root. This is a user-supplied file (defined in Phase 1), not a stub.

## Self-Check: PASSED

- FOUND: app.py
- FOUND: pyproject.toml
- FOUND: commit c9bc6a1 (chore: add streamlit and pandas)
- FOUND: commit 451212a (feat: implement app.py)
