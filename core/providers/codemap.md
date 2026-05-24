# core/providers/ — Provider Abstraction Codemap

## Responsibility
The `providers/` sub-package defines a pluggable AI provider architecture. Each provider implements the abstract `BaseProvider.run()` interface, enabling the CV tailoring pipeline to work with multiple AI backends (Claude CLI, Claude API, Gemini API, Gemini Web, OpenAI-compatible) without changing pipeline logic.

## Design Patterns

| Pattern | Implementation | Why |
|---------|---------------|-----|
| **Strategy** | `BaseProvider` ABC with `run()` abstract method | Swappable AI backends; pipeline code only depends on the interface |
| **Factory (async)** | `get_provider(model, user_id)` in `__init__.py` | Resolves per-user settings from DB, constructs the appropriate concrete provider |
| **Lazy Instantiation** | All provider `__init__` methods | API keys/settings validated at construction time, never at module import |
| **Adapter** | `ClaudeProvider` wraps `pipeline.run_pipeline()` | Adapts the legacy Claude CLI subprocess pipeline to the provider interface |
| **Template Method** | All `run()` methods follow the same pattern: build prompts → invoke API → extract JSON → validate with Pydantic → retry 3x | Consistent retry and error handling across providers |

## Provider Hierarchy

```
BaseProvider (ABC)
├── ClaudeProvider          — Claude CLI (subprocess)
├── ClaudeAPIProvider       — Anthropic SDK (API)
├── GeminiProvider          — Google GenAI SDK
├── GeminiWebProvider       — gemini-webapi (browser cookies, async)
└── OpenAIProvider          — OpenAI SDK (any OpenAI-compatible endpoint)
```

## Key Files & Symbols

| File | Key Exports | Purpose |
|------|-------------|---------|
| `base.py` | `BaseProvider` (ABC), `run()` abstract method | Interface contract: `run(BaseCV, job_text, creativity_level) → (TailoredCV, list[GapItem])` |
| `__init__.py` | `get_provider(model, user_id)` async factory | **Async factory**: lazily imports provider class, resolves per-user API keys/models from `backend.settings_cache.get_setting()`, returns configured provider instance |
| `claude_provider.py` | `ClaudeProvider` | Thin wrapper: delegates `run()` → `pipeline.run_pipeline()` with `cli_model` from per-user settings |
| `claude_api_provider.py` | `ClaudeAPIProvider`, `DEFAULT_MODEL = "claude-haiku-4-5"` | Uses `anthropic.Anthropic` SDK; `_build_system_prompt_for_chat()` + `_build_user_prompt()`; `max_tokens=16000`; catches `anthropic.APIError` |
| `gemini_provider.py` | `GeminiProvider`, `DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"` | Uses `google.genai.Client` SDK; `GenerateContentConfig(system_instruction=...)`; catches `genai_errors.APIError` |
| `gemini_web_provider.py` | `GeminiWebProvider`, `DEFAULT_MODEL = "gemini-3-flash"`, `_sanitize_gemini_output()` | Uses `gemini_webapi.GeminiClient` (browser cookie auth via `__Secure-1PSID`); sync `run()` creates `asyncio.run()` event loop; fresh client per attempt; `_sanitize_gemini_output()` cleans markdown→JSON |
| `openai_provider.py` | `OpenAIProvider`, default model `"gpt-4o-mini"` | Uses `openai.OpenAI` SDK; supports `base_url` override for OpenAI-compatible endpoints (Groq, Together AI, Ollama); catches `openai.APIError` |

## Data & Control Flow

```
get_provider("gemini-flash", user_id=42)
  │
  ├─▶ await get_setting("gemini_api_key", 42)
  ├─▶ await get_setting("gemini_model", 42)
  └─▶ return GeminiProvider(api_key=..., model=...)

provider.run(base_cv, job_text, creativity=2)
  │
  ├─▶ _build_system_prompt_for_chat(2)   ─── system prompt with creativity rules
  ├─▶ _build_user_prompt(base_cv, job)   ─── user prompt with CV YAML + job text + schema
  │
  ├─▶ API call (attempt 1)
  │   └─▶ _extract_json(response) → TailoredCV.model_validate()
  │
  ├─▶ API call (attempt 2, on failure)   ─── appended "Return ONLY valid JSON"
  │
  └─▶ return (TailoredCV, gap_diff list)
```

## Provider Configuration

| Model Key | Provider Class | Settings (per-user, from DB) | Default Model |
|-----------|---------------|------------------------------|---------------|
| `"claude-haiku"` (default) | `ClaudeProvider` | `claude_cli_model` | `"haiku"` (CLI env) |
| `"claude-api"` | `ClaudeAPIProvider` | `anthropic_api_key`, `claude_api_model` | `"claude-haiku-4-5"` |
| `"gemini-flash"` | `GeminiProvider` | `gemini_api_key`, `gemini_model` | `"gemini-3.1-flash-lite-preview"` |
| `"gemini-web"` | `GeminiWebProvider` | `gemini_web_psid`, `gemini_web_model` | `"gemini-3-flash"` |
| `"openai"` | `OpenAIProvider` | `openai_api_key`, `openai_model`, `openai_base_url` | `"gpt-4o-mini"` |

## Retry & Error Handling Pattern

All API-based providers (`ClaudeAPIProvider`, `GeminiProvider`, `OpenAIProvider`, `GeminiWebProvider`) share an identical 3-attempt retry pattern:

1. Call the SDK method with the prompt.
2. Pass raw text through `_extract_json()` (which strips fences, normalizes tailoring_notes).
3. Validate with `TailoredCV.model_validate()`.
4. On failure: log warning, append "Return ONLY valid JSON" to prompt, retry.
5. After 3 failures: raise `RuntimeError` with the last exception.

`ClaudeProvider` is the exception — it delegates to `pipeline.run_pipeline()` which has its own `_invoke_with_retry()` loop.

## Gemini Web Provider Special Handling

`GeminiWebProvider` has unique behavior:

- **Authentication**: Uses browser cookie values (`__Secure-1PSID`, `__Secure-1PSIDTS`) rather than an API key.
- **Sync wrapper**: `run()` calls `asyncio.run(self._run_async(...))` — designed to work inside `asyncio.to_thread()` (thread pool thread with no event loop).
- **Fresh client per attempt**: Web sessions become corrupted after stream suspension; a new `GeminiClient` is created for each retry.
- **Output sanitization**: `_sanitize_gemini_output()` applies 4 cleaning steps: strip markdown fences, unescape invalid JSON backslash sequences (`\_` → `_`), unwrap markdown links (`[text](url)` → `text`), extract outermost JSON via brace-depth parsing.
- **No system prompt separation**: Gemini Web API has no separate system message parameter — system and user prompts are concatenated into a single string.
- **Logging suppression**: `gemini_webapi.utils.parsing` logger is silenced to WARNING to avoid frame-parsing debug spam.
