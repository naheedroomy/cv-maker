# Phase 1005: Dockerization & docker-compose - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Containerize the entire application — backend (Python + LaTeX), frontend (Vue SPA served by Nginx), and wire them together with docker-compose and an Nginx reverse proxy that routes `/api/*` to the backend and `/` to the frontend static build.

Deliverables:
1. `Dockerfile.backend` — Python runtime, LaTeX (texlive-base), all Python dependencies via uv
2. `Dockerfile.frontend` — Multi-stage: Node build + Nginx serve
3. `docker-compose.yml` — Orchestrates backend + frontend + nginx
4. `nginx.conf` — Routes `/api/*` to backend, `/` to frontend SPA, handles SPA fallback
5. `.env.example` updated with all required env vars for Docker deployment

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key technical considerations:
- Backend needs `texlive` for LaTeX PDF compilation (latexmk)
- Backend uses `uv` for Python package management
- Frontend is a Vue 3 SPA built with Vite
- SQLite database file needs to persist across container restarts (volume mount)
- Environment variables: `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `GEMINI_API_KEY`, `CORS_ORIGINS`

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>

---

*Phase: 1005-dockerization-and-docker-compose*
*Context gathered: 2026-04-07 (infrastructure — discuss skipped)*
