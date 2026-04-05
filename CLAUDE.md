<!-- GSD:project-start source:PROJECT.md -->
## Project

**CV Maker**

An AI-powered CV tailoring pipeline that takes a structured base CV and a job listing, then uses Claude Code CLI (non-interactive mode) to produce a tailored CV. The system emphasizes and surfaces relevant skills and experience without fabricating anything — it can take liberties in highlighting tools and technologies the user actually knows. Output is rendered via LaTeX templates to PDF, with a Vue 3 SPA frontend and FastAPI backend.

**Core Value:** Given a job listing and a base CV, produce a tailored CV that honestly highlights the most relevant experience and skills — never fabricate, only emphasize and reframe.

### Constraints

- **AI Provider**: Claude Code CLI (`claude -p`) — free with existing subscription, JSON output with parse-retry
- **UI Framework**: Vue 3 SPA + FastAPI backend — component-level control, async job queue, real routing
- **Output Format**: LaTeX → PDF — professional quality, flexible templates
- **Honesty**: AI must never fabricate experience or skills — only reframe, emphasize, and surface existing ones
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### AI / LLM Layer
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Claude Code CLI (`claude -p`) | latest | AI backbone — generates tailored CV content via subprocess | Free with existing Claude subscription; `--model haiku` for speed; JSON output with parse-retry loop; no SDK or API key required. |
| Model: `haiku` | latest | LLM for CV tailoring | Fastest Claude model; invoked via `claude -p --model haiku --no-session-persistence`; sufficient quality for CV rewriting tasks. |
| `google-genai` | >=1.70.0 | Gemini SDK — secondary AI provider for CV tailoring | Strategy pattern abstraction; Gemini 3.1 Flash-Lite Preview as alternative to Claude CLI; requires GEMINI_API_KEY. |
| Model: `gemini-3.1-flash-lite-preview` | latest | Secondary LLM for CV tailoring | Faster alternative via API; selected in frontend model dropdown; lazy API key loading. |

### Structured Data Layer (Base CV)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| YAML | — | Storage format for the base CV | Human-editable without a UI; clean diff history in git; better readability than JSON for structured documents. The base CV is maintained by hand, so authoring experience matters. |
| `PyYAML` | 6.x | Parse YAML into Python dicts | Standard, ubiquitous, no additional schema enforcement needed at this layer. |
| `pydantic` | 2.12.5 | Validate and model the parsed base CV; define response schemas for Claude JSON output | Pydantic v2 serves double duty: (1) validates the YAML base CV on load, catching malformed input early; (2) defines the response schemas used to validate JSON output from Claude CLI. The two uses share the same model definitions. |

### UI Layer
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Vue 3 | ^3.5.31 | Frontend SPA — job listing input, status tracking, PDF preview/download | Reactive component model; TypeScript-first; mature ecosystem. Replaced Streamlit in v2.0 for richer interactivity. |
| Pinia | ^3.0.4 | State management | Official Vue store; setup-store pattern with `storeToRefs` for reactive destructuring. |
| Vue Router | ^5.0.4 | Client-side routing | Standard Vue routing solution. |
| Vite | ^8.0.3 | Build tool and dev server | Instant HMR; native ESM; TypeScript support out of the box. |
| TypeScript | ~6.0.0 | Type safety for frontend | Catches errors at compile time; `vue-tsc` for Vue SFC type checking. |

### Backend Layer
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | >=0.135.3 | REST API server | Async-native; automatic OpenAPI docs; Pydantic model integration for request/response validation. |
| uvicorn | >=0.43.0 | ASGI server | Standard production server for FastAPI; supports `--reload` for development. |
| aiosqlite | >=0.22.1 | Async SQLite access | Non-blocking database operations; WAL mode + busy_timeout for concurrent writes; lightweight — no external DB server needed. |

### PDF Generation Layer
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `Jinja2` | 3.x | Render LaTeX template with tailored CV data | Industry-standard templating; LaTeX delimiter conflict is solved by a one-time Jinja2 environment configuration (see below). Widely used for exactly this pattern. |
| `latexmk` (system binary) | via MacTeX / TeX Live | Compile `.tex` → `.pdf` | Handles multi-pass compilation automatically (bibliography, cross-references). Part of MacTeX on macOS, part of TeX Live on Linux. No Python wrapper needed — call via `subprocess`. |
| `subprocess` (stdlib) | — | Call `latexmk` | No wrapper library justified — `subprocess.run(["latexmk", "-pdf", ...])` is two lines and gives full control over error output. |
| `tempfile` (stdlib) | — | Isolate each compilation in a temp directory | Prevents auxiliary file pollution (`*.aux`, `*.log`) in the working directory. Each render gets a clean `mkdtemp()` directory, deleted after PDF bytes are read. |

### Configuration / Secrets
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `python-dotenv` | >=1.2.2 | Load `.env` file into environment at startup | Enables local GEMINI_API_KEY config without exporting in shell; `load_dotenv()` called in `backend/main.py` before FastAPI app initialization. |
| Environment variables | — | Runtime configuration | `GEMINI_API_KEY` for Gemini provider (optional — graceful degradation). Claude CLI uses existing subscription (no key needed). |

### Developer Tooling
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `uv` | latest | Package management, virtual environment, lockfile | 10–100x faster than pip; `uv.lock` gives reproducible installs; `pyproject.toml`-native. The modern standard for Python project setup in 2025. |
| `ruff` | latest | Linting + formatting | Replaces black + flake8 + isort in one tool; extremely fast. |
| Python | 3.12 | Runtime | Stable LTS target. Supported by all stack libraries. 3.13+ is available but offers no meaningful benefit here and may have fewer pre-built wheels for some LaTeX-adjacent tools. |
| `pytest` + `httpx` | latest | Testing | pytest for unit tests; httpx for async FastAPI test client. |

## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| AI provider | Claude Code CLI (primary) | Gemini 3.1 Flash-Lite (secondary) | Both supported via strategy pattern; Claude is free with subscription, Gemini requires API key but is faster |
| AI provider | Claude Code CLI | OpenAI API | Same reason — CLI approach avoids SDK dependencies and API key overhead |
| UI framework | Vue 3 + Vite | Streamlit | Streamlit lacks component-level control, real routing, and state management needed for job queue UI with polling |
| UI framework | Vue 3 + Vite | React + Vite | Vue's composition API and SFC model are simpler for a solo-dev project of this size |
| Backend | FastAPI | Flask | FastAPI is async-native; automatic OpenAPI docs; built-in Pydantic integration |
| Database | aiosqlite (SQLite) | PostgreSQL | SQLite is zero-config, sufficient for single-user workload; WAL mode handles concurrent reads/writes |
| Base CV format | YAML + PyYAML + Pydantic | JSON | YAML is more readable and writable by hand; the CV will be authored/edited manually |
| Base CV format | YAML | TOML | TOML lacks good multi-line string support needed for bullet points and summaries |
| PDF generation | LaTeX + latexmk | WeasyPrint | HTML/CSS-to-PDF; harder to achieve professional typesetting; LaTeX is the project constraint |
| PDF generation | LaTeX + latexmk | ReportLab | Programmatic PDF building; no separation of template and content; poor typographic defaults |
| PDF generation | Jinja2 + subprocess | PyLaTeX | PyLaTeX builds LaTeX programmatically, fighting against template-based design |
| Package manager | `uv` | `pip` + `venv` | uv is faster, manages lockfile automatically, and is the current best practice |

## Installation
```bash
# Backend setup with uv
uv sync

# Frontend setup
cd frontend && npm install

# MacTeX (includes latexmk, pdflatex, xelatex)
# macOS: brew install --cask mactex
# Verify latexmk is on PATH
which latexmk
```

## Confidence Assessment
| Component | Confidence | Source | Notes |
|-----------|------------|--------|-------|
| Claude Code CLI (`claude -p --model haiku`) | HIGH | Direct usage in pipeline.py | Proven in production; parse-retry handles JSON extraction reliably |
| Vue 3.5 + Pinia 3 + Vite 8 | HIGH | package.json + working frontend | Standard modern Vue stack; TypeScript 6.0 |
| FastAPI + uvicorn + aiosqlite | HIGH | pyproject.toml + working backend | Async pipeline runner wraps subprocess via asyncio.to_thread |
| Pydantic 2.12.5 | HIGH | PyPI official metadata | Used for CV models and API validation |
| Jinja2 + LaTeX delimiter reconfiguration pattern | MEDIUM | Multiple community sources; pattern is well-established but no single authoritative doc | Pattern is stable and widely used for CV/resume generation |
| latexmk via subprocess + tempfile | MEDIUM | Multiple technical sources; latexmk is MacTeX bundled | Correct approach; latexmk must be verified installed on target machine |
| `uv` as package manager | HIGH | Official Astral docs + widespread community adoption in 2025 | |
| `google-genai` + Gemini 3.1 Flash-Lite | HIGH | pyproject.toml + working provider | Strategy pattern provider; lazy API key; parse-retry with Pydantic validation |

## Sources
- [Claude Code CLI docs](https://docs.anthropic.com/en/docs/claude-code)
- [Vue 3 documentation](https://vuejs.org/)
- [Pinia documentation](https://pinia.vuejs.org/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [aiosqlite on PyPI](https://pypi.org/project/aiosqlite/)
- [Vite documentation](https://vite.dev/)
- [Pydantic on PyPI](https://pypi.org/project/pydantic/)
- [Pydantic Settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [LaTeX templates with Jinja2](https://13rac1.com/articles/2015/11/latex-templates-python-and-jinja2-generate-pdfs/)
- [Generating reports with Jinja, LaTeX and Docker](https://www.leospairani.com/blog/2024/04/16/generating-reports-with-jinja-latex-and-docker/)
- [uv documentation](https://docs.astral.sh/uv/)
- [google-genai SDK](https://pypi.org/project/google-genai/)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
