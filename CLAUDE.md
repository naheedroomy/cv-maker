<!-- GSD:project-start source:PROJECT.md -->
## Project

**CV Maker**

An AI-powered CV tailoring pipeline that takes a structured base CV and a job listing, then uses Claude Code CLI (non-interactive mode) to produce a tailored CV. The system emphasizes and surfaces relevant skills and experience without fabricating anything — it can take liberties in highlighting tools and technologies the user actually knows. Output is rendered via LaTeX templates to PDF, with a simple Streamlit UI.

**Core Value:** Given a job listing and a base CV, produce a tailored CV that honestly highlights the most relevant experience and skills — never fabricate, only emphasize and reframe.

### Constraints

- **AI Provider**: Claude Code CLI (`claude -p`) — free with existing subscription, JSON output with parse-retry
- **UI Framework**: Streamlit — simple, Python-native
- **Output Format**: LaTeX → PDF — professional quality, flexible templates
- **Honesty**: AI must never fabricate experience or skills — only reframe, emphasize, and surface existing ones
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### AI / LLM Layer
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `google-genai` | 1.70.0 | Gemini API client — generates tailored CV content | The unified, current SDK. The older `google-generativeai` package is deprecated as of 2025. `google-genai` covers both Gemini Developer API and Vertex AI under one interface. |
| Model: `gemini-2.5-flash-lite` | GA | LLM for CV tailoring | Fastest and most cost-efficient model in the 2.5 family; 1M token context window; optional thinking budget (0–24,576 tokens). Matches the project's hard constraint. |
### Structured Data Layer (Base CV)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| YAML | — | Storage format for the base CV | Human-editable without a UI; clean diff history in git; better readability than JSON for structured documents. The base CV is maintained by hand, so authoring experience matters. |
| `PyYAML` | 6.x | Parse YAML into Python dicts | Standard, ubiquitous, no additional schema enforcement needed at this layer. |
| `pydantic` | 2.12.5 | Validate and model the parsed base CV; define response schemas for Gemini structured output | Pydantic v2 serves double duty: (1) validates the YAML base CV on load, catching malformed input early; (2) defines the `response_schema` passed to Gemini, guaranteeing structured JSON output from the LLM. The two uses share the same model definitions. |
### UI Layer
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `streamlit` | 1.56.0 | Full UI — job listing input, trigger, preview, download | Python-native; zero frontend code; script-level reruns make LLM call orchestration simple. Hard-constrained by the project. |
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
| `pydantic-settings` | 2.x | Load and validate `GEMINI_API_KEY` and other config from environment / `.env` file | Type-checked config; automatically reads `.env` via built-in dotenv support; eliminates `os.environ.get()` scattered through code. One import, one `Settings` class. |
### Developer Tooling
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `uv` | latest | Package management, virtual environment, lockfile | 10–100x faster than pip; `uv.lock` gives reproducible installs; `pyproject.toml`-native. The modern standard for Python project setup in 2025. |
| `ruff` | latest | Linting + formatting | Replaces black + flake8 + isort in one tool; extremely fast. |
| Python | 3.12 | Runtime | Stable LTS target. Supported by all stack libraries. 3.13+ is available but offers no meaningful benefit here and may have fewer pre-built wheels for some LaTeX-adjacent tools. |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Gemini SDK | `google-genai` | `google-generativeai` | Officially deprecated in 2025; no new features will be added |
| Gemini SDK | `google-genai` | `langchain-google-genai` | LangChain adds abstraction overhead with no benefit for a single-provider, single-task pipeline |
| Base CV format | YAML + PyYAML + Pydantic | JSON | YAML is more readable and writable by hand; the CV will be authored/edited manually |
| Base CV format | YAML | TOML | TOML lacks good multi-line string support needed for bullet points and summaries |
| PDF generation | LaTeX + latexmk | WeasyPrint | HTML/CSS-to-PDF; harder to achieve professional typesetting; LaTeX is the project constraint |
| PDF generation | LaTeX + latexmk | ReportLab | Programmatic PDF building; no separation of template and content; poor typographic defaults |
| PDF generation | Jinja2 + subprocess | PyLaTeX | PyLaTeX builds LaTeX programmatically, fighting against template-based design |
| Structured output | Pydantic `response_schema` | Prompt engineering for JSON | Pydantic schema guarantees valid, parseable output; prompt engineering alone is fragile |
| Env management | `pydantic-settings` | `python-dotenv` | pydantic-settings includes dotenv support AND type validation; python-dotenv alone requires manual `os.environ.get()` calls everywhere |
| Package manager | `uv` | `pip` + `venv` | uv is faster, manages lockfile automatically, and is the current best practice |
## Installation
# Project setup with uv
# Core runtime dependencies
# Dev dependencies
# MacTeX (includes latexmk, pdflatex, xelatex)
# Verify latexmk is on PATH
## Confidence Assessment
| Component | Confidence | Source | Notes |
|-----------|------------|--------|-------|
| `google-genai` 1.70.0, `gemini-2.5-flash-lite` GA | HIGH | PyPI + ai.google.dev official docs | Verified: google-generativeai is deprecated; model is GA |
| Pydantic `response_schema` with Gemini | HIGH | Official google-genai docs + Gemini API structured output docs | Native support confirmed for all 2.5 models |
| Streamlit 1.56.0, Python >=3.10 | HIGH | PyPI official metadata | Version confirmed; Python 3.9 dropped in 2025 releases |
| Pydantic 2.12.5 | HIGH | PyPI official metadata | |
| Jinja2 + LaTeX delimiter reconfiguration pattern | MEDIUM | Multiple community sources; pattern is well-established but no single authoritative doc | Pattern is stable and widely used for CV/resume generation |
| latexmk via subprocess + tempfile | MEDIUM | Multiple technical sources; latexmk is MacTeX bundled | Correct approach; latexmk must be verified installed on target machine |
| `uv` as package manager | HIGH | Official Astral docs + widespread community adoption in 2025 | |
| `pydantic-settings` for env management | HIGH | Official Pydantic docs | |
## Sources
- [Google GenAI Python SDK — Official Docs](https://googleapis.github.io/python-genai/)
- [google-genai on PyPI](https://pypi.org/project/google-genai/)
- [Gemini API Models](https://ai.google.dev/gemini-api/docs/models)
- [Gemini 2.5 Flash Lite on Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-lite)
- [Gemini Structured Output docs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Streamlit on PyPI](https://pypi.org/project/streamlit/)
- [Streamlit 2025 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- [Streamlit st.download_button docs](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button)
- [Pydantic on PyPI](https://pypi.org/project/pydantic/)
- [Pydantic Settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [LaTeX templates with Jinja2](https://13rac1.com/articles/2015/11/latex-templates-python-and-jinja2-generate-pdfs/)
- [Generating reports with Jinja, LaTeX and Docker](https://www.leospairani.com/blog/2024/04/16/generating-reports-with-jinja-latex-and-docker/)
- [uv documentation](https://docs.astral.sh/uv/)
- [Developer's guide to Gemini 2.5 Flash-Lite](https://medium.com/google-cloud/developers-guide-to-getting-started-with-gemini-2-5-flash-lite-8795eed5486c)
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
