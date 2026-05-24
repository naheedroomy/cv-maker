# data/

## Responsibility

The `data/` directory holds the user's **canonical base CV** — a YAML file (`base_cv.yaml`) that serves as the single source of truth for all CV tailoring, AI prompt construction, LaTeX rendering, and PDF generation throughout the pipeline. Every bullet, skill, and role in every generated CV traces back to this file. It also acts as a **seed file** for first-time setup: if missing, the backend auto-creates a placeholder at startup.

## Schema / Shape

`base_cv.yaml` is a YAML serialization of the `BaseCV` Pydantic v2 model defined in `core/models.py`. The top-level keys and their shapes:

| Key | Shape | Notes |
|-----|-------|-------|
| `contact` | `ContactInfo` | `name`, `email` (required); `linkedin`, `github`, `phone`, `location`, `work_authorization` (optional) |
| `summary` | `str` | Professional summary paragraph; coerced to `""` if `null` in YAML |
| `experience` | `list[ExperienceItem]` | Each item: `company`, `title`, `start` (YYYY-MM string), `end` (YYYY-MM or `null`=current), `bullets` (list of achievements), `technologies` (per-role tool list), `location` (optional) |
| `skills` | `list[str]` | Flat list of technologies/tools across all experience |
| `education` | `list[EducationItem]` | Each item: `institution`, `degree`, `field` (optional), `year` (int, optional) |
| `projects` | `list[ProjectItem]` | Each item: `name`, `description`, `technologies`, `url` (optional) |
| `certifications` | `list[str]` | Flat list of certification strings |
| `languages` | `list[LanguageItem]` | Each item: `language`, `level` (e.g., "C2", "Native") |

**Validation constraints** enforced by Pydantic on load:
- `contact.name` and `contact.email` are required — missing fields raise `ValidationError`.
- `summary` coerces `null` to `""`.
- Dates (`start`/`end`) are stored as `"YYYY-MM"` strings. PyYAML's automatic `datetime.date` coercion is reversed by a `@field_validator` so the string format is always preserved.
- `education.year` must be `int | None` — strings are rejected.
- All list fields default to `[]` if absent.

**Current shape** (185 lines in the repo):
- 1 `contact` block (name, email, GitHub, LinkedIn, phone, location)
- 1 `summary` (paragraph of professional experience)
- 5 `experience` entries (reverse chronological, `2025-07`–`2019-07` across 4 companies)
- `skills`: 24 technologies
- `education`: 1 entry (BSc Computer Science, University of Westminster, 2021)
- `certifications`: 2 entries (CKAD earned, CKA expected)
- `projects`: empty list `[]`

## Data & Control Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ STARTUP                                                         │
│ backend/main.py :: lifespan()                                   │
│   └─ ensure_base_cv_exists()  →  creates placeholder if missing │
└───────────────────┬─────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────────┐
│ LOAD (every pipeline run)                                       │
│ backend/worker.py :: job_worker()                               │
│   1. DB-FIRST: SELECT base_cv_yaml FROM users WHERE id=?        │
│      └─ if found → BaseCV.model_validate(raw)                   │
│   2. FILE FALLBACK: load_base_cv("data/base_cv.yaml")           │
│      └─ yaml.safe_load() → BaseCV.model_validate(raw)           │
│                                                                 │
│ backend/routers/cv.py :: get_cv_me() / get_cv_info()            │
│   Same DB-first-then-file pattern for read/display endpoints    │
│                                                                 │
│ backend/routers/cover_letter.py :: _cover_letter_worker()       │
│   Uses load_base_cv() for additional CV context in generation   │
└───────────────────┬─────────────────────────────────────────────┘
                    │  BaseCV instance
┌───────────────────▼─────────────────────────────────────────────┐
│ AI PIPELINE                                                     │
│ core/pipeline.py :: _serialize_base_cv()                        │
│   base_cv.model_dump() → yaml.dump() → embedded in AI prompt    │
│   └─ Claude/Gemini/OpenAI reads the full CV as context          │
│   └─ Produces TailoredCV with gap_diff, tailoring_notes         │
│                                                                 │
│ core/cv_converter.py :: convert_cv_to_yaml()                    │
│   Parses plain-text/pasted CV → BaseCV via LLM → YAML saved     │
└───────────────────┬─────────────────────────────────────────────┘
                    │  TailoredCV
┌───────────────────▼─────────────────────────────────────────────┐
│ RENDER                                                          │
│ core/renderer.py :: render_latex(tailored_cv)                   │
│   Jinja2 template (cv.tex.jinja) + TailoredCV → LaTeX source   │
│   └─ render_pdf(latex_source) → latexmk → PDF bytes            │
└─────────────────────────────────────────────────────────────────┘
```

**Write paths** that update `base_cv.yaml` or the per-user equivalent:
- `POST /api/cv/upload` — PDF parsed via Gemini → `BaseCV` → saved to `users.base_cv_yaml` (DB)
- `PUT /api/cv/me` — edited CV JSON → validated as `BaseCV` → saved to DB
- `POST /api/cv/convert` — plain-text CV → LLM parsing → `save_base_cv()` writes to disk (`data/base_cv.yaml`)
- `DELETE /api/cv/me` — sets `users.base_cv_yaml = NULL` in DB (falls back to file)

## Integration Points

| Module | Function / Symbol | Role |
|--------|------------------|------|
| `core/data.py` | `load_base_cv(path)` | Primary loader: reads YAML, validates against `BaseCV`, returns `BaseCV` instance. Raises `FileNotFoundError` if missing, `RuntimeError` on invalid YAML. |
| `core/data.py` | `ensure_base_cv_exists(path)` | Idempotent creator: writes a placeholder `BaseCV` YAML structure if the file doesn't exist. Called at app startup. |
| `core/data.py` | `DEFAULT_CV_PATH` | `Path(os.environ.get("BASE_CV_PATH", "data/base_cv.yaml"))` — overridable via env var. |
| `core/models.py` | `BaseCV` | Pydantic v2 model: canonical schema. Every reader and writer in the system validates against this class. |
| `core/models.py` | `ExperienceItem` | Sub-model with date coercion validator (`coerce_date_to_string`) that handles PyYAML's datetime leakage. |
| `core/pipeline.py` | `_serialize_base_cv(cv)` | Converts `BaseCV` → YAML string for embedding in AI prompt templates. Used by both Claude CLI and chat-based providers. |
| `core/pipeline.py` | `run_pipeline(base_cv, ...)` | Public entry point: takes `BaseCV` + job text, returns `TailoredCV` + gap diff. |
| `core/cv_converter.py` | `convert_cv_to_yaml(cv_text)` | LLM-powered parser: plain-text CV → `BaseCV`. Supports Claude CLI and API providers. |
| `core/cv_converter.py` | `save_base_cv(cv, path)` | Serializes a `BaseCV` instance to disk as YAML. Default path is `DEFAULT_CV_PATH`. |
| `backend/main.py` | `lifespan()` | Calls `ensure_base_cv_exists()` on startup. Logs the resolved `DEFAULT_CV_PATH`. |
| `backend/worker.py` | `job_worker()` | **DB-first load**: checks `users.base_cv_yaml`, falls back to `load_base_cv()`. Feeds the `BaseCV` into the AI pipeline. |
| `backend/routers/cv.py` | `get_cv_me()`, `put_cv_me()`, `delete_cv_me()`, `upload_cv()` | CRUD for per-user CV stored as YAML text in the SQLite `users` table. |
| `backend/routers/cv_convert.py` | `get_cv_info()`, `convert_cv()` | Read CV info (DB-first, file-fallback); parse + save plain-text CV to disk. |
| `backend/routers/cover_letter.py` | `_cover_letter_worker()` | Loads base CV via `load_base_cv()` for cover letter generation context. |
| `backend/db.py` | `users.base_cv_yaml` | SQLite TEXT column storing the per-user CV as a YAML string. |
| `tests/conftest.py` | `base_cv_path` fixture | Points to `data/base_cv.yaml` for integration tests. |
| `tests/test_models.py` | `test_load_base_cv_*` | Validates file-not-found, successful load, and invalid-YAML error paths. |

## Operational Notes

- **Git-tracked**: `data/base_cv.yaml` is checked into version control and contains real CV data. Treat it as sensitive — don't share the repo publicly without scrubbing.
- **Env override**: Set `BASE_CV_PATH` to use a different file path (e.g., in Docker: `BASE_CV_PATH=/app/data/base_cv.yaml`).
- **DB vs File precedence**: The worker always tries the DB first (`users.base_cv_yaml` column). If a user has uploaded or edited their CV, that per-user version takes priority over the file. The file serves as a system-wide default/fallback.
- **Placeholder auto-creation**: If `base_cv.yaml` is deleted or doesn't exist, `ensure_base_cv_exists()` writes a minimal valid `BaseCV` structure with empty strings and empty lists. This prevents the app from crashing on first run.
- **YAML pitfalls**: Dates like `2021-03` are interpreted as `datetime.date` by PyYAML unless quoted. The `coerce_date_to_string` validator in `ExperienceItem` converts them back to `"YYYY-MM"` strings transparently. Keep date values quoted in the YAML: `start: "2021-03"`.
- **Pydantic v2 validation**: `load_base_cv()` uses `model_validate()` (strict) rather than `model_construct()` (lax). Malformed YAML surfaces all field errors at once in the `RuntimeError` message prefixed with `"base_cv.yaml failed validation:"`.
- **Multi-provider loading**: Both the Claude CLI pipeline (`core/pipeline.py`) and API-based pipeline (`core/pipeline.py::_build_user_prompt`) serialize `BaseCV` to YAML for their respective prompt formats. The `BaseCV` model itself is provider-agnostic.
- **Tests**: `tests/test_models.py` contains dedicated tests for the file load path (`DATA-01` success criteria), including invalid YAML error messages and missing-file handling. Tests use the actual repo file at `data/base_cv.yaml`.
