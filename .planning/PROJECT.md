# CV Maker

## What This Is

An AI-powered CV tailoring pipeline that takes a structured base CV and a job listing, then uses Claude Code CLI (non-interactive mode) to produce a tailored CV. The system emphasizes and surfaces relevant skills and experience without fabricating anything. Output is rendered via LaTeX templates to PDF, with a Vue.js SPA frontend and FastAPI backend supporting concurrent job generation with real-time status tracking.

## Core Value

Given a job listing and a base CV, produce a tailored CV that honestly highlights the most relevant experience and skills — never fabricate, only emphasize and reframe.

## Requirements

### Validated

- ✓ User can define a structured base CV containing all experience, skills, and tools — v1.0 Phase 1
- ✓ Claude Code CLI pipeline (analyze job + tailor CV, JSON parse-retry) — v1.0 Phase 3
- ✓ LaTeX rendering pipeline (Jinja2 template, escape, PDF compilation) — v1.0 Phase 2
- ✓ Pydantic data models (BaseCV, TailoredCV, GapItem, JobAnalysis) — v1.0 Phase 1+3
- ✓ FastAPI backend with async endpoints — v2.0 Phase 5
- ✓ SQLite database with WAL mode for persistent storage — v2.0 Phase 5
- ✓ Background job queue with real-time SSE status updates — v2.0 Phase 6
- ✓ Full REST API (create, list, detail, cancel, PDF download, SSE) — v2.0 Phase 6
- ✓ Vue.js SPA frontend with Pinia state management — v2.0 Phase 7
- ✓ Session history sidebar with real-time updates — v2.0 Phase 7
- ✓ CV preview and gap diff display in browser — v2.0 Phase 7
- ✓ Single uvicorn command serves API + SPA — v2.0 Phase 8
- ✓ Structured backend logging visible in terminal — v2.0 Phase 5

### Active

(None — planning next milestone)

### Out of Scope

- Job listing URL scraping — copy-paste is sufficient
- Multiple CV format templates — one good template first
- User accounts / authentication — personal tool
- Job application tracking — this is a CV generator, not an ATS
- Production-grade infrastructure — personal tool, functional is sufficient
- Axios HTTP client — supply chain compromise (use native fetch)

## Context

- Personal tool for the user to tailor their CV when applying to jobs
- Claude Code CLI chosen as AI backend — free with existing Claude subscription
- LaTeX chosen for flexible, professional-quality PDF output
- v1.0 used Streamlit — replaced in v2.0 with Vue.js + FastAPI
- v2.0 shipped: FastAPI backend, Vue 3 SPA, SQLite persistence, background job queue, SSE real-time updates
- Tech stack: Python 3.12 (FastAPI, aiosqlite, Pydantic v2) + Vue 3 (Vite, Pinia, Vue Router)
- 2,780 Python LOC + 1,409 Vue/TS LOC

## Constraints

- **AI Provider**: Claude Code CLI (`claude -p`) — free with existing subscription, JSON output with parse-retry
- **Frontend**: Vue.js SPA — proper state management, concurrent sessions
- **Backend**: FastAPI — async, concurrent job handling, structured logging
- **Database**: SQLite — zero-config persistence for sessions and CV data
- **Output Format**: LaTeX → PDF — professional quality, flexible templates
- **Honesty**: AI must never fabricate experience or skills — only reframe, emphasize, and surface existing ones

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Claude Code CLI over Gemini API | Free with existing subscription, high quality output | ✓ Good |
| LaTeX for output | Professional typesetting, flexible templates | ✓ Good |
| Streamlit for v1 UI | Minimal frontend effort for prototype | ⚠️ Replaced in v2.0 |
| Vue.js + FastAPI for v2 | Streamlit rerun model breaks concurrent sessions | ✓ Good |
| SQLite over MongoDB | Zero-config, no server process, sufficient for personal use | ✓ Good |
| asyncio.to_thread for blocking calls | Wraps subprocess.run (Claude CLI, latexmk) without blocking event loop | ✓ Good |
| asyncio.create_task + set registry | GC-safe background tasks, not FastAPI BackgroundTasks | ✓ Good |
| Native fetch (no Axios) | Axios supply chain compromise (UNC1069, 2026-03-31) | ✓ Good |
| Plain CSS over Tailwind | Personal tool, minimal deps, scoped styles sufficient | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-04-04 after v2.0 Full-Stack Rebuild milestone complete*
