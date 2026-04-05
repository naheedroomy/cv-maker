# CV Maker

AI-powered CV tailoring pipeline. Takes a structured base CV and a job listing, uses AI to produce a tailored CV that highlights relevant experience, and renders it to PDF via LaTeX.

Supports multiple AI providers: Claude Code CLI, Claude API, Gemini, and OpenAI.

## Quick Start (Docker)

The easiest way to run CV Maker. No need to install Python, Node, LaTeX, or any dependencies.

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
git clone https://github.com/nroo6394/cv-maker.git
cd cv-maker

# Copy and configure environment
cp .env.example .env
# Edit .env — add API keys for the providers you want to use

# Build and run
docker compose up --build
```

Open http://localhost:8000 in your browser.

### Docker Details

- **Single container** — backend (FastAPI) and built frontend (Vue) are served together on port 8000
- **Data persists** across container restarts and rebuilds via Docker volumes:
  - `cv-data` — SQLite database (jobs, settings)
  - `output-data` — generated PDF files
- **`base_cv.yaml`** is bind-mounted — edit it locally without rebuilding
- Only `docker compose down -v` deletes volumes and wipes data
- To rebuild after code changes: `docker compose up --build`

### Docker Limitations

Claude Code CLI provider is not available inside Docker (requires an authenticated `claude` binary on the host). Use Claude API, Gemini, or OpenAI providers instead.

## Local Development Setup

Use this if you want to develop or prefer running without Docker.

### Prerequisites

- **Python 3.12+**
- **Node.js 22.12+**
- **uv** (Python package manager)
- **MiKTeX** (Windows) or **MacTeX** (macOS) — for LaTeX/PDF compilation
- **Claude Code CLI** (optional) — `claude` must be on PATH and authenticated

### Install uv

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install LaTeX

- **Windows**: Install [MiKTeX](https://miktex.org/download). Set "Install missing packages on the fly" to Yes.
- **macOS**: `brew install --cask mactex-no-gui`
- **Linux**: `sudo apt install texlive-xetex texlive-fonts-recommended texlive-latex-extra latexmk`

### Install Dependencies

```bash
# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

### Running Locally

Open two terminals:

**Backend (FastAPI):**

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Backend runs at http://localhost:8000. API docs at http://localhost:8000/docs.

**Frontend (Vue + Vite):**

```bash
cd frontend
npm run dev
```

Frontend runs at http://localhost:5173. API requests proxy to the backend automatically.

## AI Providers

CV Maker supports 4 AI providers. Configure which models to use in the Settings page (http://localhost:8000/settings or http://localhost:5173/settings).

| Provider | Config Key | API Key Env Var | Default Model | Notes |
|---|---|---|---|---|
| **Claude Code** | `claude-haiku` | None (uses CLI auth) | `haiku` | Free with Claude subscription. Not available in Docker. |
| **Claude API** | `claude-api` | `ANTHROPIC_API_KEY` | `claude-haiku-4-5` | Direct API access. Models: `claude-haiku-4-5`, `claude-sonnet-4-6`, `claude-opus-4-6` |
| **Gemini** | `gemini-flash` | `GEMINI_API_KEY` | `gemini-2.5-flash` | Google AI. Models: `gemini-2.5-flash`, `gemini-2.5-pro` |
| **OpenAI** | `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` | Also works with OpenAI-compatible APIs (Groq, Together AI, Ollama) via Base URL |

### Settings Page

Model names and the OpenAI base URL are configurable in the UI at `/settings` — no need to restart the server. API keys are set via `.env` (secrets stay out of the database).

## Usage

1. Edit `base_cv.yaml` with your complete experience (this is your source of truth)
2. Open the app in your browser
3. Enter a company name, job link (optional), and paste the job listing text
4. Select an AI provider and submit
5. View the tailored CV, gap analysis, and tailoring notes
6. Download the generated PDF
7. Use **Regenerate** buttons to try different providers on the same job

## Project Structure

```
cv-maker/
  backend/            # FastAPI app — routes, DB, worker, settings
  frontend/           # Vue 3 + Vite + Pinia SPA
  src/cv_maker/       # Core library — pipeline, models, LaTeX renderer
    providers/        # AI provider implementations (Claude, Gemini, OpenAI)
    templates/        # LaTeX Jinja2 templates
  base_cv.yaml        # Your base CV (edit this)
  Dockerfile          # Multi-stage build (Node + Python + TeX Live)
  docker-compose.yml  # Single-service deployment with persistent volumes
  .env.example        # Template for API key configuration
```
