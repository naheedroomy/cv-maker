# Roadmap: CV Maker

## Overview

Build a linear pipeline that takes a structured YAML base CV and a pasted job listing, runs it through Claude Code CLI to produce a tailored CV, renders it to PDF via LaTeX, and wraps the whole thing in a Streamlit UI. The build order is deliberately bottom-up: data contracts first, then the renderer (isolated from AI), then the Claude Code CLI pipeline, then the UI that wires everything together. History and layout features ship with the UI phase since they depend on the full pipeline being in place.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Foundation** - Define the YAML base CV schema and Pydantic models that all downstream components share (completed 2026-04-03)
- [ ] **Phase 2: LaTeX Renderer** - Build the Jinja2 + LaTeX + subprocess render pipeline in isolation before adding AI variability
- [ ] **Phase 3: AI Pipeline** - Integrate Claude Code CLI for job analysis, CV tailoring, no-fabrication enforcement, and gap diff
- [x] **Phase 4: Streamlit UI** - Wire all components into a working Streamlit app with session state, history, and PDF download (completed 2026-04-04)

## Phase Details

### Phase 1: Data Foundation
**Goal**: The base CV schema and shared data models are defined, validated, and ready to be consumed by all downstream components
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02
**Success Criteria** (what must be TRUE):
  1. A YAML file containing the user's full base CV loads without errors and validates against the Pydantic BaseCV model
  2. Invalid base CV fields (missing required keys, wrong types) are caught at load time with a clear error message
  3. The job listing can be represented as a plain string that flows through the pipeline without transformation
  4. All shared Pydantic models (BaseCV, JobRequirements, TailoredCV) are importable and instantiable with test data
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Scaffold uv project, define all Pydantic models, write YAML loader, sample base_cv.yaml, and pytest tests

### Phase 2: LaTeX Renderer
**Goal**: Given a TailoredCV data object, the renderer produces a valid PDF — independent of any AI component
**Depends on**: Phase 1
**Requirements**: OUT-01, OUT-02
**Success Criteria** (what must be TRUE):
  1. A hardcoded TailoredCV object renders to a PDF that opens and displays correctly formatted CV content
  2. LaTeX special characters in CV content (ampersands, percent signs, underscores) are escaped and do not break compilation
  3. The render function returns PDF bytes that can be written to disk or served via Streamlit download
  4. A LaTeX compilation error surfaces a readable error message rather than a silent failure
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Install MacTeX + Jinja2, build renderer.py (escape_latex, render_latex, render_pdf) and cv.tex.jinja template
- [ ] 02-02-PLAN.md — Write test_renderer.py and human checkpoint to verify PDF visual output

### Phase 3: AI Pipeline
**Goal**: Given a base CV and a job listing, Claude Code CLI produces a tailored CV JSON object and a gap diff — with no fabricated content
**Depends on**: Phase 2
**Requirements**: AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07, DATA-03, LAY-01
**Success Criteria** (what must be TRUE):
  1. Pasting a real job listing produces a TailoredCV where every bullet point references only skills and experience present in the base CV
  2. The gap diff correctly identifies job requirements the base CV does not cover and flags them to the user
  3. Claude Code CLI is invoked with `claude -p` in non-interactive mode and returns parseable JSON; a malformed response triggers a retry and eventually a clear error
  4. Skills and technologies present in the base CV but not featured in the work experience are surfaced in the tailored output when relevant to the job
  5. CV sections are reordered in the output to lead with the most relevant content for the target job
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Extend models.py with GapItem and JobAnalysis Pydantic models
- [x] 03-02-PLAN.md — Implement pipeline.py with two-step Claude invocation, retry loop, and no-fabrication enforcement
- [x] 03-03-PLAN.md — Write test_pipeline.py with monkeypatched subprocess tests

### Phase 4: Streamlit UI
**Goal**: Users can run the full pipeline — paste a job listing, generate a tailored CV, preview it, download the PDF, and revisit past runs — entirely through a browser UI
**Depends on**: Phase 3
**Requirements**: UI-01, UI-02, OUT-03, OUT-04, HIST-01, HIST-02
**Success Criteria** (what must be TRUE):
  1. User pastes a job listing, clicks Generate, and receives a downloadable tailored PDF without leaving the browser
  2. Interacting with Streamlit widgets (scrolling, clicking non-Generate buttons) does not re-trigger Claude Code CLI calls
  3. User can preview the tailored CV content in the UI before downloading the PDF
  4. Past (job listing, tailored CV) pairs are stored locally and the user can browse and open any previous run
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Install streamlit + pandas, implement app.py with session_state guard, gap table, CV preview, PDF download
- [x] 04-02-PLAN.md — Add history save/load and sidebar browser to app.py; human smoke test checkpoint

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 1/1 | Complete   | 2026-04-03 |
| 2. LaTeX Renderer | 1/2 | In Progress|  |
| 3. AI Pipeline | 1/3 | In Progress|  |
| 4. Streamlit UI | 2/2 | Complete   | 2026-04-04 |
