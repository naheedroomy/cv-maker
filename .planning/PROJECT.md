# CV Maker

## What This Is

An AI-powered CV tailoring pipeline that takes a structured base CV and a job listing, then uses AI (Claude Code CLI or Gemini 3.1 Flash-Lite Preview) to produce a tailored CV. The system emphasizes and surfaces relevant skills and experience without fabricating anything. Output is rendered via LaTeX templates to PDF, with a Vue 3 SPA frontend and FastAPI backend supporting concurrent job generation with real-time status tracking.

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
- ✓ Gemini 3.1 Flash-Lite Preview as alternative AI provider with model selector — v2.0 Phase 9
- ✓ Strategy pattern provider abstraction (BaseProvider, ClaudeProvider, GeminiProvider) — v2.0 Phase 9
- ✓ Capability detection via /api/config endpoint — v2.0 Phase 9

### Active

(None — planning next milestone)

### Out of Scope

- Job listing URL scraping — copy-paste is sufficient
- Multiple CV format templates — one good template first
- User accounts / authentication — personal tool
- Job application tracking — this is a CV generator, not an ATS
- Production-grade infrastructure — personal tool, functional is sufficient
- Axios HTTP client — supply chain compromise (use native fetch)
- Docker containerization — personal local tool

## Context

- Personal tool for the user to tailor their CV when applying to jobs
- v1.0: Streamlit prototype with Claude Code CLI AI backend (shipped 2026-04-04)
- v2.0: Full-stack rebuild — Vue 3 + FastAPI + SQLite + Gemini provider (shipped 2026-04-05)
- Tech stack: Python 3.12 (FastAPI, aiosqlite, Pydantic v2, google-genai, python-dotenv) + Vue 3 (Vite, Pinia, Vue Router, TypeScript)
- 3,159 Python LOC + 1,947 Vue/TS LOC across 59 files
- Two AI providers: Claude Code CLI (free with subscription) and Gemini 3.1 Flash-Lite Preview (API key)

## Constraints

- **AI Provider**: Claude Code CLI (`claude -p`) primary; Gemini 3.1 Flash-Lite Preview secondary — Strategy pattern abstraction
- **Frontend**: Vue 3 SPA — proper state management, concurrent sessions
- **Backend**: FastAPI — async, concurrent job handling, structured logging
- **Database**: SQLite — zero-config persistence for sessions and CV data
- **Output Format**: LaTeX -> PDF — professional quality, flexible templates
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
| Strategy pattern for providers | Clean abstraction for multi-provider support; shared prompt extraction | ✓ Good |
| Lazy Gemini API key loading | Missing GEMINI_API_KEY only fails at call time, not server startup | ✓ Good |
| Capability detection via /api/config | Frontend gracefully degrades when Gemini unavailable | ✓ Good |
| Idempotent SQLite migrations | PRAGMA table_info guard prevents errors on repeated startups | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-04-05 after v2.0 Full-Stack Rebuild milestone complete*
