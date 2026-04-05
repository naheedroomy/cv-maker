# Stage 1: Build frontend
FROM node:22-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build-only

# Stage 2: Python runtime with TeX Live
FROM python:3.12-slim

# Install TeX Live (minimal + needed packages) and system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-latex-extra \
    latexmk \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ src/
COPY backend/ backend/
COPY base_cv.yaml ./

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Create output directory
RUN mkdir -p output

# Default port
EXPOSE 8000

# Run with uv so the virtualenv is activated
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
