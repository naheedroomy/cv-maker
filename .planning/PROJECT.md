# CV Maker

## What This Is

An AI-powered CV tailoring pipeline that takes a structured base CV and a job listing, then uses Google Gemini 2.5 Flash Lite to produce a tailored CV. The system emphasizes and surfaces relevant skills and experience without fabricating anything — it can take liberties in highlighting tools and technologies the user actually knows. Output is rendered via LaTeX templates to PDF, with a simple Streamlit UI.

## Core Value

Given a job listing and a base CV, produce a tailored CV that honestly highlights the most relevant experience and skills — never fabricate, only emphasize and reframe.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can define a structured base CV containing all experience, skills, and tools
- [ ] User can paste a job listing into the UI
- [ ] System uses Gemini 2.5 Flash Lite to analyze the job listing and tailor the CV
- [ ] AI emphasizes relevant skills/tools without fabricating experience
- [ ] AI can surface tools/technologies the user knows but didn't prominently feature
- [ ] Output is rendered to PDF via LaTeX templates
- [ ] Simple Streamlit UI for the full workflow
- [ ] User can preview and download the tailored CV

### Out of Scope

- Job listing URL scraping — copy-paste is sufficient for v1
- Multiple CV format templates — one good template first
- User accounts / authentication — personal tool
- Job application tracking — this is a CV generator, not an ATS

## Context

- Personal tool for the user to tailor their CV when applying to jobs
- Google Gemini 2.5 Flash Lite chosen for cost-efficiency and speed
- LaTeX chosen for flexible, professional-quality PDF output
- Streamlit chosen for rapid UI development with minimal frontend work
- The "base CV" is a complete inventory — everything the user has ever done, all skills, all tools — so the AI has maximum material to work with

## Constraints

- **AI Provider**: Google Gemini 2.5 Flash Lite — cost-effective, fast inference
- **UI Framework**: Streamlit — simple, Python-native
- **Output Format**: LaTeX → PDF — professional quality, flexible templates
- **Honesty**: AI must never fabricate experience or skills — only reframe, emphasize, and surface existing ones

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Gemini 2.5 Flash Lite over other LLMs | Cost-efficient, fast, good enough for CV tailoring | — Pending |
| LaTeX for output | Professional typesetting, flexible templates, clean PDF output | — Pending |
| Streamlit for UI | Minimal frontend effort, Python-native, good enough for personal tool | — Pending |
| Structured base CV as input | Gives AI maximum material to work with when tailoring | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-04 after initialization*
