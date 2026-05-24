# core/ — Shared Library Codemap

## Responsibility
The `core/` package is the shared, UI-free engine of cv-maker. It owns all data models, AI pipeline orchestration, LaTeX/PDF rendering, cover letter generation, CV parsing (PDF→structured data), and provider abstractions. Every downstream component (Streamlit UI, backend API, tests) imports exclusively from this package.

## Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Pydantic v2 models** | `models.py` | Single source of truth for all structured data; validation at boundaries |
| **Pipeline (batch)** | `pipeline.py` → `run_pipeline()` | Single-function entry point: BaseCV + job text → TailoredCV + gap diff |
| **Strategy (providers)** | `providers/base.py` → `BaseProvider` | Abstract `run()` interface; 5 concrete providers with per-user key resolution |
| **Template Method** | `renderer.py` | Jinja2 rendering: TailoredCV → LaTeX string (`render_latex`) → PDF bytes (`render_pdf`) |
| **Factory (async)** | `providers/__init__.py` → `get_provider()` | Async factory: resolves per-user settings from DB, constructs correct provider |
| **Two-pass pipeline** | `cv_parser.py` → `parse_pdf_to_base_cv()` | PDF: pymupdf (image extraction) → Gemini (OCR) → Gemini (structuring) |
| **Chain of Responsibility** | `pipeline.py` → `_extract_json()` | Extracts JSON from LLM output; handles markdown fences, normalizes tailoring_notes |

## Data & Control Flow

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   data.py        │     │  pipeline.py    │     │  renderer.py     │
│ load_base_cv()   │────▶│ run_pipeline()  │────▶│ render_latex()   │──▶ LaTeX string
│ BaseCV ← YAML     │     │ BaseCV+job→AI   │     │ TailoredCV→LaTeX │
└──────────────────┘     │ →TailoredCV     │     └────────┬─────────┘
                         └────────┬────────┘              │
                                  │               render_pdf()         │
                         ┌────────▼────────┐              │
                         │  cover_letter.py│     ┌────────▼─────────┐
                         │generate_cover_  │     │    PDF bytes     │
                         │   letter()      │     └──────────────────┘
                         │ → plain text    │
                         └────────────────┘
┌──────────────────┐
│  cv_converter.py │     ┌──────────────────┐
│ convert_cv_to_   │     │  cv_parser.py    │
│   yaml()         │     │parse_pdf_to_base │
│ text→AI→BaseCV   │     │   _cv()          │
└──────────────────┘     │ PDF→Gemini→BaseCV│
                         └──────────────────┘
```

1. **Load**: `data.py` reads `base_cv.yaml` → validates into `BaseCV` Pydantic model.
2. **Tailor**: `pipeline.py` builds a parameterized prompt (7 creativity levels), invokes the configured AI provider, parses the JSON response into a `TailoredCV` with `gap_diff`.
3. **Render**: `renderer.py` feeds `TailoredCV` through a Jinja2 LaTeX template (`cv.tex.jinja`), producing a PDF via `latexmk -xelatex`.
4. **Cover Letter** (optional): `cover_letter.py` takes the `TailoredCV`, gap diff, and tone selection, generates a plain-text cover letter.
5. **Import**: `cv_converter.py` or `cv_parser.py` converts external CVs (plain text or PDF) into a `BaseCV`.

## Key Files & Symbols

| File | Key Exports | Purpose |
|------|-------------|---------|
| `models.py` | `BaseCV`, `TailoredCV`, `ContactInfo`, `ExperienceItem`, `GapItem`, `TailoringNote`, `EducationItem`, `ProjectItem`, `LanguageItem`, `JobRequirements`, `JobAnalysis` | Canonical Pydantic v2 data models for the entire pipeline |
| `pipeline.py` | `run_pipeline()`, `Creativity` (IntEnum), `_build_prompt()`, `_build_system_prompt_for_chat()`, `_build_user_prompt()`, `_extract_json()`, `_invoke_with_retry()`, `_serialize_base_cv()`, `_RULES` dict | AI tailoring engine: prompt construction, creativity level rule resolution, JSON parse-retry, Claude CLI orchestration |
| `renderer.py` | `render_latex()`, `render_pdf()`, `escape_latex()`, `escape_latex_with_bold()`, `escape_latex_strip_bold()`, `_find_latexmk()` | LaTeX rendering: Jinja2 template rendering, LaTeX special-char escaping (single-pass regex), bold→`\textbf{}` conversion, `latexmk` binary discovery |
| `data.py` | `load_base_cv()`, `ensure_base_cv_exists()`, `DEFAULT_CV_PATH` | YAML loading with Pydantic v2 validation; placeholder creation |
| `cv_converter.py` | `convert_cv_to_yaml()`, `save_base_cv()`, `_invoke_provider()` | Plain-text CV → BaseCV via AI provider; supports Claude CLI, Claude API, Gemini, OpenAI |
| `cv_parser.py` | `parse_pdf_to_base_cv()`, `_pdf_to_images()`, `_ocr_images()`, `_structure_text()` | Two-pass PDF CV parsing: pymupdf → page images → Gemini OCR → Gemini structuring → BaseCV |
| `cover_letter.py` | `generate_cover_letter()`, `CoverLetterOutput`, `SYSTEM_PROMPT_TEMPLATE`, `USER_PROMPT_TEMPLATE`, `_TONE_INSTRUCTIONS` | Cover letter generation: 6 tone profiles, anti-AI writing rules, 3-step process (draft→self-critique→rewrite), provider-agnostic including Gemini Web |
| `cover_letter_renderer.py` | `render_cover_letter_pdf()` | Cover letter → PDF via fpdf2 (pure Python, no LaTeX dependency); latin-1 sanitization |

## Integration Points

- **Streamlit UI** (Phase 4): Consumes `load_base_cv()`, `run_pipeline()`, `render_latex()`, `render_pdf()`, `generate_cover_letter()`, `convert_cv_to_yaml()`, `parse_pdf_to_base_cv()`.
- **Backend API** (`backend/`): Uses `get_provider()` async factory for per-user key resolution from `backend/settings_cache`.
- **Tests** (`tests/`): Import models, pipeline helpers (`_extract_json`), renderer (`escape_latex`), and provider classes for unit testing.
- **Environment**: Requires `BASE_CV_PATH` (default `data/base_cv.yaml`), `GEMINI_API_KEY` (PDF parsing), provider-specific API keys.

## Operational Notes

- **Creativity levels**: `pipeline.py` defines a 7-level `Creativity` IntEnum (0=STRICT through 6=CREATIVE). The `_RULES` dict maps each concern (titles, bullets, skills, summary, inference, substitution, pruning, tone, reorder, core_competencies) to per-level instructions. `_resolve_rule()` picks the instruction for the highest defined threshold ≤ the requested level.
- **Prompt architecture**: Two prompt builders: `_build_prompt()` (single combined prompt for Claude CLI) and `_build_system_prompt_for_chat()` + `_build_user_prompt()` (system/user split for chat-based providers). Both share the same `_RULES` resolution.
- **JSON parse-retry**: `_invoke_with_retry()` retries up to 3 times. On retries, appends "Return ONLY valid JSON" to the prompt. `_extract_json()` strips markdown fences and normalizes tailoring_notes from plain strings to structured dicts.
- **LaTeX escaping**: `escape_latex()` uses a single-pass regex substitution against all 10 LaTeX special chars simultaneously, preventing cascading (e.g., `\textbackslash{}` braces won't be re-escaped). Registered as Jinja2 filters: `|e` (plain escape), `|be` (escape + bold), `|se` (strip bold then escape).
- **TailoredCV._strip_annotation_leaks()**: A `@model_validator(mode="after")` that strips action labels like `(substituted)` or `(soft-fabricated)` from bullet text that LLMs sometimes leak.
- **Gemini Web sanitization**: `GeminiWebProvider._sanitize_gemini_output()` strips markdown fences, invalid JSON backslash escapes, unwraps markdown links, and extracts the outermost JSON object via brace matching — needed because the Gemini web API returns markdown-formatted output.
- **Provider selection**: The async factory in `providers/__init__.py` only imports provider classes inside `get_provider()`, ensuring missing API keys only error when a specific provider is actually requested, not at server startup.
