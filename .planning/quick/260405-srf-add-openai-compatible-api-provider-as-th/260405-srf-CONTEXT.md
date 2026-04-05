# Quick Task 260405-srf: Add OpenAI-compatible API provider - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Task Boundary

Add OpenAI-compatible API provider as a third model option, following the existing Strategy pattern (BaseProvider). Enables broad compatibility with OpenAI, Groq, Together AI, Ollama, etc.

</domain>

<decisions>
## Implementation Decisions

### SDK Choice
- Use the official `openai` Python package with `base_url` override for endpoint flexibility
- Supports any OpenAI-compatible API (Groq, Together AI, Ollama, etc.) via base_url param

### Configuration UX
- 3 environment variables in .env: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`
- All 3 required for the provider to be enabled (availability gated on OPENAI_API_KEY presence)
- Follow existing pattern: lazy loading at call time, not startup

### UI Label
- Toggle button label: "OpenAI"
- Hint text should explain it works with any OpenAI-compatible API endpoint

</decisions>

<specifics>
## Specific Ideas

- Follow exact same pattern as GeminiProvider: lazy client init, 3-attempt retry, _build_prompt + _extract_json reuse
- Add `openai_available` flag to GET /api/config response
- ModelSelector.vue gets a third button with same disabled/enabled gating pattern
- Value string: "openai" (matches factory routing in get_provider)

</specifics>
