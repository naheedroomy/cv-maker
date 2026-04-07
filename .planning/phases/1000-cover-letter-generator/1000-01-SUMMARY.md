---
phase: "1000-cover-letter-generator"
plan: "01"
subsystem: "backend-core"
tags: ["cover-letter", "prompt-engineering", "fpdf2", "pydantic", "db-migration"]
dependency_graph:
  requires: []
  provides:
    - "CoverLetterOutput Pydantic model"
    - "generate_cover_letter() function for all 4 providers"
    - "render_cover_letter_pdf() fpdf2 renderer"
    - "cover_letter_text and cover_letter_notes DB columns"
    - "CoverLetterRequest and CoverLetterResponse API schemas"
  affects:
    - "backend/schemas.py"
    - "backend/db.py"
tech_stack:
  added:
    - "fpdf2>=2.8.7 — pure Python text-to-PDF renderer"
  patterns:
    - "Two-pass self-critique in single LLM prompt (adversarial reviewer framing)"
    - "Anti-AI-smell rules with concrete BAD/GOOD examples for all 10 rules"
    - "Tone-parameterized prompt via _TONE_INSTRUCTIONS dict (same pattern as pipeline.py _RULES)"
    - "Provider-agnostic generation: Claude CLI via _invoke_with_retry, chat providers via _client access"
    - "Idempotent SQLite migration via PRAGMA table_info guard"
    - "Unicode sanitization (latin-1 safe) for fpdf2 built-in fonts"
key_files:
  created:
    - "src/cv_maker/cover_letter.py"
    - "src/cv_maker/cover_letter_renderer.py"
  modified:
    - "backend/db.py"
    - "backend/schemas.py"
    - "pyproject.toml"
    - "uv.lock"
decisions:
  - "Standalone generate_cover_letter() function rather than adding run_cover_letter() to BaseProvider ABC — different signature, avoids forcing all 4 providers to implement a second method"
  - "Two-pass self-critique embedded in single prompt (not two API calls) — 80% quality gain at single-call latency"
  - "fpdf2 over LaTeX/WeasyPrint for cover letter PDF — pure Python, zero system deps, 60 lines for clean output"
  - "Unicode sanitization (replace em dash/curly quotes) over TTF font addition — simpler for cover letter use case"
metrics:
  duration: "162s"
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_created: 2
  files_modified: 4
---

# Phase 1000 Plan 01: Cover Letter Generation Backend Core Summary

## One-liner

Backend core for cover letter generation: anti-AI-smell prompt module with 10 rules and BAD/GOOD examples, two-pass adversarial self-critique, fpdf2 text-to-PDF renderer, idempotent DB migration, and Pydantic API schemas.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Create cover letter generation module with anti-AI-smell prompt and two-pass self-critique | 7c3ffbf | src/cv_maker/cover_letter.py |
| 2 | Create fpdf2 PDF renderer, add DB migration, and add API schemas | a112f06 | src/cv_maker/cover_letter_renderer.py, backend/db.py, backend/schemas.py, pyproject.toml |

## What Was Built

### `src/cv_maker/cover_letter.py`

- `CoverLetterOutput` Pydantic model with `cover_letter_text`, `self_critique`, `revision_notes` fields
- `ANTI_AI_RULES` constant: 10 rules with concrete BAD/GOOD examples (significance inflation, promotional language, simple verbs, rule-of-three, generic conclusions, -ing padding, filler, sentence rhythm, opinions vs hedging, specificity)
- `_TONE_INSTRUCTIONS` dict: four tone fragments (formal/professional/confident/casual) following the `_RULES` dict pattern from pipeline.py
- `_build_cover_letter_prompt()`: returns (system_prompt, user_prompt) tuple with two-pass adversarial self-critique — "hostile AI-detection reviewer" framing, "find at least 3 AI tells", explicitly marks tailored CV as PRIMARY source
- `generate_cover_letter()`: provider-agnostic entry point — Claude CLI uses `_invoke_with_retry`, chat providers (claude-api, gemini-flash, openai) use their `_client` directly with 3-attempt retry loop

### `src/cv_maker/cover_letter_renderer.py`

- `_sanitize_text()`: replaces 9 common Unicode characters (em dash, en dash, curly quotes, ellipsis, bullet, NBSP) with latin-1 equivalents for fpdf2 built-in font compatibility
- `render_cover_letter_pdf()`: fpdf2-based renderer with professional margins (25mm), optional candidate name header (bold 14pt), body text (Helvetica 11pt), paragraph-based multi_cell layout

### `backend/db.py`

- Two new idempotent migration blocks after the `creativity_level` migration:
  - `cover_letter_text TEXT` column
  - `cover_letter_notes TEXT` column
- Follow exact PRAGMA table_info guard pattern used by existing migrations

### `backend/schemas.py`

- `CoverLetterRequest`: model, tone (pattern-validated enum: formal/professional/confident/casual), user_notes
- `CoverLetterResponse`: cover_letter_text, cover_letter_notes
- `JobResponse` updated: added `cover_letter_text: str | None = None` and `cover_letter_notes: str | None = None`

## Decisions Made

1. **Standalone function over ABC method**: `generate_cover_letter()` is a module-level function, not added to `BaseProvider.run()`. The existing `.run()` returns `tuple[TailoredCV, list[GapItem]]`; cover letter has a completely different signature. Adding to the ABC would force all 4 providers to implement a second method unnecessarily.

2. **Single-prompt two-pass self-critique**: Both draft generation and adversarial review happen within one LLM call via prompt instructions. Research shows ~80% of multi-call quality gain at single-call latency. The "hostile reviewer" framing and "find at least 3" instruction counter the model's tendency to evaluate its own output favorably.

3. **fpdf2 for PDF rendering**: Pure Python, zero system dependencies, ~60 lines for professional output. LaTeX would be overkill (temp dirs, compilation, escaping); WeasyPrint requires system C libs.

4. **Unicode sanitization**: Replaces 9 common Unicode chars before rendering rather than adding a TTF font. Cover letters are mostly ASCII; LLM output may include curly quotes and em dashes. Sanitization keeps the implementation simple and avoids bundling font files.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all exported functions are fully implemented. The renderer produces valid PDF bytes; the generation function handles all 4 providers. Database migration adds both columns. API schemas include tone validation.

## Self-Check: PASSED

- `src/cv_maker/cover_letter.py` exists: FOUND
- `src/cv_maker/cover_letter_renderer.py` exists: FOUND
- Commit 7c3ffbf (Task 1): FOUND
- Commit a112f06 (Task 2): FOUND
- All imports verified: `from cv_maker.cover_letter import CoverLetterOutput, generate_cover_letter` OK
- PDF header verified: `pdf[:4] == b'%PDF'` OK
- Schemas verified: `from backend.schemas import CoverLetterRequest, CoverLetterResponse` OK
- BAD/GOOD examples: 10 each confirmed
