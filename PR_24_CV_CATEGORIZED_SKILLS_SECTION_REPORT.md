# PR #24 Follow-up Report: Categorized Skills Section & 15-Skill Curation Ceiling

## Executive Summary
This update redesigns the Skills section across the AI pipeline, data models, LaTeX template renderer, and the manual CV editor. Instead of generating an overcrowded, unformatted blob of 20+ comma-separated technologies that resembles keyword stuffing, skills are now curated into **3–4 clean, logical categories** with a strict programmatic ceiling of **15 skills total** across all categories combined.

---

## Changes Implemented

### 1. AI Pipeline & Prompt Rules (`core/pipeline.py`)
- **`_RULES["skills_injection"]`**:
  - Updated all 4 creativity levels (0–3) to instruct the model:
    - **Categorized Structure**: Group skills into 3–4 logical domains formatted as `"<Category Name>: <Skill 1>, <Skill 2>, <Skill 3>"` (e.g. *Platforms & Cloud*, *DevOps & IaC*, *Languages & Frameworks*, *Observability & Reliability*).
    - **15-Skill Total Ceiling**: Enforce an upper limit of 15 skills across all categories combined (typically 3–5 high-impact skills per category).
    - **Exclusion of Table-Stakes Tooling**: Exclude routine developer utilities (e.g. Conventional Commits, Git, Bash, npm, Jira, Slack, basic Linux CLI) unless explicitly central to the JD.
    - **JD Prioritization**: Select technologies most relevant and high-impact for the target job description that complement rather than repeat bullet points.
- **`_RULES["keyword_policy"]`**:
  - Replaced the generic skills dump warning with strict anti-stuffing rules requiring domain categorization and the 15-skill total cap.
- **Prompt JSON Schemas**:
  - Updated schema descriptions in `_build_prompt`, `_build_user_prompt`, and Stage 3 generator:
    `"skills": ["<Category: Skill 1, Skill 2, Skill 3> (3-4 categories, max 15 skills total)"]`.

### 2. Defensive Pydantic Validation & Normalization (`core/models.py`)
- Added `@field_validator("skills", mode="before")` on `TailoredCV`:
  - Normalizes whatever format the LLM outputs (`dict[str, list[str]]`, `[{"category": "...", "skills": [...]}]`, or strings) into standard `"<Category>: <items>"` strings.
- Added `@field_validator("skills", mode="after")` on `TailoredCV`:
  - Counts individual comma-separated skills across all categories.
  - Case-insensitively deduplicates.
  - Strictly clamps the total across all categories to a maximum of 15 individual skills.

### 3. LaTeX Template & PDF Rendering (`core/templates/cv.tex.jinja`)
- Transformed `\section{Skills}` from a flat comma-separated line into structured category blocks:
  ```latex
  \BLOCK{if cv.skills}
  \bigskip
  \section{Skills}
  \BLOCK{for skill in cv.skills}
  \BLOCK{if ":" in skill}
  \BLOCK{set parts = skill.split(":", 1)}
  \textbf{\VAR{parts[0].strip()|e}:} \VAR{parts[1].strip()|e}\BLOCK{if not loop.last}\\[2pt]\BLOCK{endif}
  \BLOCK{else}
  \VAR{skill|e}\BLOCK{if not loop.last}, \BLOCK{endif}
  \BLOCK{endif}
  \BLOCK{endfor}
  \BLOCK{endif}
  ```
- Backwards-compatible: plain strings without colons continue to render as comma-separated text.

### 4. Audit & Validation Engine (`core/validation.py`)
- Updated `_check_keywords` to extract individual skills from category strings (`"Category: item1, item2"`) when checking for unsubstantiated keywords, preventing false positive warnings against category lines.

### 5. Frontend Preview & Manual Editor (`CvPreview.vue` & `CvFormEditor.vue`)
- **`CvPreview.vue`**:
  - Renders categorized skills with bold category labels (`<strong>Category:</strong> Skills`).
- **`CvFormEditor.vue`**:
  - Upgraded the Skills section from a flat list of tags to category cards:
    - Dynamic section title showing real-time count: `Skills & Technologies (X / 15)`.
    - Category name input and individual skill tags per category.
    - `+ Add Category` and `+ Add skill` controls.
    - Hard disable on adding skills once 15 skills are reached.
    - Helpful guidance text on omitting routine utilities.

---

## Verification & Testing
- `uv run pytest`: **276 passed**, 5 skipped in 1.10s.
  - `tests/test_models.py`: Tested normalization of dicts/lists of dicts, deduplication, and 15-skill ceiling.
  - `tests/test_pipeline.py`: Tested prompt builders for categorized instructions, 15-skill limit, and routine tool exclusion.
  - `tests/test_renderer.py`: Tested LaTeX rendering of categorized skills with bold headers and flat backwards compatibility.
  - `tests/test_validation.py`: Tested verified and unverified skills inside category strings.
- `cd frontend && npm run build`: `vue-tsc --build` and `vite build` completed with 0 errors.
