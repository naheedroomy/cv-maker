---
phase: quick-260407-hg6
plan: 01
subsystem: ai, pdf
tags: [tcolorbox, xcolor, latex, pills, pydantic, prompt-engineering]

requires:
  - phase: none
    provides: existing TailoredCV model and LaTeX template
provides:
  - core_competencies field on TailoredCV model
  - Core Competencies pill section in LaTeX template
  - Bullet reordering rule in AI prompts
  - Anti-pruning rule in AI prompts
affects: [pipeline, renderer, templates]

tech-stack:
  added: [tcolorbox, xcolor]
  patterns: [conditional LaTeX sections, pill/tag rendering with tcolorbox]

key-files:
  created: []
  modified:
    - src/cv_maker/models.py
    - src/cv_maker/pipeline.py
    - src/cv_maker/templates/cv.tex.jinja
    - tests/conftest.py
    - tests/test_renderer.py

key-decisions:
  - "Used tcolorbox \\newtcbox for pill styling — light teal background, dark text, rounded corners"
  - "Placed Core Competencies between Summary and Experience for recruiter scan visibility"
  - "All three new rules (reorder, core_competencies, pruning) apply at level 0+ for universal effect"

patterns-established:
  - "Conditional LaTeX section: BLOCK{if cv.field} ... BLOCK{endif} pattern for optional sections"
  - "Pill rendering: \\pill{escaped-text}\\hspace{2pt}% for inline wrapped tags"

requirements-completed: [CC-01, BR-01, OP-01]

duration: 3min
completed: 2026-04-07
---

# Quick Task 260407-hg6: Core Competencies Pills, Bullet Reorder, Anti-Pruning Summary

**Core Competencies pill section with tcolorbox, bullet reordering by JD relevance, and anti-pruning bias toward inclusion in all 3 prompt paths**

## Performance

- **Duration:** 3 min 30 sec
- **Started:** 2026-04-07T07:08:39Z
- **Completed:** 2026-04-07T07:12:09Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `core_competencies: list[str]` optional field to TailoredCV model with empty default for backward compatibility
- Added three new AI rules (reorder, core_competencies, pruning) wired into all 3 prompt paths: `_build_prompt`, `_build_system_prompt_for_chat`, `_build_user_prompt`
- Built Core Competencies pill section in LaTeX template using tcolorbox with teal background, rounded corners, and sans-serif font
- Section is conditional -- renders only when core_competencies is non-empty
- Added 4 new tests: pill presence, pill absence (empty list), ampersand escaping in pills, PDF compilation with pills

## Task Commits

Each task was committed atomically:

1. **Task 1: Model + prompt changes** - `48c1cc6` (feat)
2. **Task 2: LaTeX template pill section + renderer update** - `3d451c2` (feat)

## Files Created/Modified
- `src/cv_maker/models.py` - Added core_competencies field to TailoredCV
- `src/cv_maker/pipeline.py` - Added reorder, core_competencies, pruning rules; wired into all 3 prompt builders; added core_competencies to JSON schemas
- `src/cv_maker/templates/cv.tex.jinja` - Added xcolor/tcolorbox packages, \pill command, conditional Core Competencies section
- `tests/conftest.py` - Added tailored_cv_with_competencies fixture
- `tests/test_renderer.py` - Added 4 new tests for pill rendering and compilation

## Decisions Made
- Used tcolorbox `\newtcbox` for pill styling rather than manual colorbox -- provides better control over padding, arc, and inline behavior
- Placed Core Competencies between Summary and Experience for maximum recruiter visibility during initial scan
- All three new rules apply at creativity level 0+ so they activate universally regardless of creativity setting
- No renderer.py code changes needed -- existing `|e` filter handles special char escaping in pills

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Issues Encountered

Two pre-existing test failures were observed (not caused by this change):
- `test_load_base_cv_success` - relies on base_cv.yaml file not present in worktree
- `test_render_pdf_raises_file_not_found_when_latexmk_missing` - expects `mactex-no-gui` in error message but actual error says `MacTeX`

Both skipped during verification; all 97 other tests pass.

## User Setup Required

None - no external service configuration required.

## Next Readiness
- Core Competencies pills are ready for end-to-end testing with a real CV generation
- The AI models will now return core_competencies arrays when processing job listings
- Bullet reordering and anti-pruning rules are active at all creativity levels

## Self-Check: PASSED

All files exist, all commits verified, all content checks pass. 97/99 tests pass (2 pre-existing failures skipped).

---
*Quick task: 260407-hg6*
*Completed: 2026-04-07*
