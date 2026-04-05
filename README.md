# CV Maker

AI-powered CV tailoring pipeline. Takes a structured base CV and a job listing, uses Claude Code CLI to produce a tailored CV, and renders it to PDF via LaTeX.

## Prerequisites

- **Python 3.12+**
- **Node.js 22.12+**
- **uv** (Python package manager)
- **MiKTeX** (Windows) or **MacTeX** (macOS) — for LaTeX/PDF compilation
- **Claude Code CLI** — `claude` must be on PATH and authenticated

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

## Setup

```bash
# Clone and enter project
git clone https://github.com/nroo6394/cv-maker.git
cd cv-maker

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend
npm install
cd ..
```

## Running Locally

Open two terminals:

### Backend (FastAPI)

```bash
cd cv-maker
uv run uvicorn backend.main:app --reload --port 8000
```

Backend runs at http://localhost:8000. API docs at http://localhost:8000/docs.

### Frontend (Vue + Vite)

```bash
cd cv-maker/frontend
npm run dev
```

Frontend runs at http://localhost:5173. API requests are proxied to the backend automatically.

## Docker (Recommended)

No need to install Python, Node, LaTeX, or any dependencies manually.

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Build and run
docker compose up --build
```

App runs at http://localhost:8000. Database and PDFs persist across restarts via Docker volumes.

**Note:** Claude CLI provider requires an authenticated `claude` binary, which isn't available inside Docker. Use Claude API, Gemini, or OpenAI providers instead (set the corresponding API keys in `.env`).

To rebuild after code changes:

```bash
docker compose up --build
```

## Usage

1. Open http://localhost:5173
2. Enter a company name, job link (optional), and paste the job listing text
3. Submit — the pipeline will tailor your CV and generate a PDF
4. Download the PDF from the job detail view

## Project Structure

```
cv-maker/
  backend/          # FastAPI app — routes, DB, worker
  frontend/         # Vue 3 + Vite + Pinia
  src/cv_maker/     # Core library — pipeline, models, LaTeX renderer
  base_cv.yaml      # Your base CV (edit this)
  output/           # Generated PDFs (gitignored)
```
