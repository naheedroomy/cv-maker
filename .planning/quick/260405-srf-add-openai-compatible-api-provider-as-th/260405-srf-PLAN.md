---
phase: quick-260405-srf
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/cv_maker/providers/openai_provider.py
  - src/cv_maker/providers/__init__.py
  - backend/routers/config.py
  - frontend/src/components/ModelSelector.vue
  - frontend/src/views/JobFormView.vue
  - .env
autonomous: true
requirements: [OPENAI-PROVIDER]
must_haves:
  truths:
    - "Selecting 'OpenAI' model and submitting a job routes through OpenAIProvider"
    - "OpenAI button is disabled when OPENAI_API_KEY is not set"
    - "OpenAI button is enabled and selectable when OPENAI_API_KEY is set"
    - "OpenAI provider produces a valid TailoredCV using the same prompt and JSON extraction as other providers"
  artifacts:
    - path: "src/cv_maker/providers/openai_provider.py"
      provides: "OpenAIProvider class implementing BaseProvider"
      contains: "class OpenAIProvider"
    - path: "src/cv_maker/providers/__init__.py"
      provides: "Factory routing for 'openai' model string"
      contains: "OpenAIProvider"
    - path: "backend/routers/config.py"
      provides: "openai_available flag in GET /api/config"
      contains: "openai_available"
    - path: "frontend/src/components/ModelSelector.vue"
      provides: "Third toggle button labeled 'OpenAI'"
      contains: "openai"
  key_links:
    - from: "frontend/src/views/JobFormView.vue"
      to: "ModelSelector.vue"
      via: "openaiAvailable prop"
      pattern: "openaiAvailable"
    - from: "frontend/src/views/JobFormView.vue"
      to: "GET /api/config"
      via: "fetch on mount"
      pattern: "openai_available"
    - from: "src/cv_maker/providers/__init__.py"
      to: "src/cv_maker/providers/openai_provider.py"
      via: "get_provider factory"
      pattern: "model == .openai."
---

<objective>
Add an OpenAI-compatible API provider as a third model option in CV Maker, following the existing Strategy pattern (BaseProvider).

Purpose: Enable users to use any OpenAI-compatible API (OpenAI, Groq, Together AI, Ollama, etc.) for CV tailoring via base_url override.
Output: Working OpenAIProvider class, factory routing, config endpoint flag, and UI toggle button.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/260405-srf-add-openai-compatible-api-provider-as-th/260405-srf-CONTEXT.md

<interfaces>
<!-- Key types and contracts the executor needs. -->

From src/cv_maker/providers/base.py:
```python
class BaseProvider(ABC):
    @abstractmethod
    def run(self, base_cv: BaseCV, job_text: str) -> tuple[TailoredCV, list[GapItem]]:
        """Run the CV tailoring pipeline. Returns (tailored_cv, gap_diff)."""
        ...
```

From src/cv_maker/pipeline.py (shared helpers):
```python
def _extract_json(text: str) -> dict:  # line 51
def _build_prompt(base_cv: BaseCV, job_text: str) -> str:  # line 95
```

From src/cv_maker/providers/__init__.py (factory to extend):
```python
def get_provider(model: str) -> BaseProvider:
    if model == "gemini-flash":
        return GeminiProvider()
    return ClaudeProvider()  # default for "claude-haiku" and any unknown value
```

From backend/routers/config.py (config endpoint to extend):
```python
@router.get("")
async def get_config():
    return {"gemini_available": bool(os.environ.get("GEMINI_API_KEY"))}
```

From frontend/src/components/ModelSelector.vue (props interface):
```typescript
defineProps<{
  modelValue: string
  geminiAvailable: boolean
  disabled: boolean
}>()
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Install openai package and create OpenAIProvider</name>
  <files>src/cv_maker/providers/openai_provider.py, src/cv_maker/providers/__init__.py, backend/routers/config.py, .env</files>
  <action>
1. Run `uv add openai` to install the official openai Python package.

2. Create `src/cv_maker/providers/openai_provider.py` following the EXACT pattern of `gemini_provider.py`:
   - Import `openai` (the package provides `OpenAI` client class).
   - Import `BaseCV`, `GapItem`, `TailoredCV` from `cv_maker.models`.
   - Import `_build_prompt`, `_extract_json` from `cv_maker.pipeline`.
   - Import `BaseProvider` from `cv_maker.providers.base`.
   - Class `OpenAIProvider(BaseProvider)`:
     - `__init__`: Read `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` from `os.environ.get()`. Raise `RuntimeError("OPENAI_API_KEY environment variable is not set")` if key is missing. Set `OPENAI_BASE_URL` default to `None` (which uses official OpenAI API). Set `OPENAI_MODEL` default to `"gpt-4o-mini"`. Create `self._client = openai.OpenAI(api_key=api_key, base_url=base_url)` — only pass `base_url` kwarg if it is not None. Store model in `self._model`.
     - `run(self, base_cv, job_text)`: Same 3-attempt retry loop as GeminiProvider. Build prompt via `_build_prompt(base_cv, job_text)`. On retry, append the "Return ONLY valid JSON" suffix. Call `self._client.chat.completions.create(model=self._model, messages=[{"role": "user", "content": effective_prompt}])`. Extract text from `response.choices[0].message.content`. Pass to `_extract_json()` then `TailoredCV.model_validate()`. Catch `openai.APIError` and generic `Exception` (matching Gemini pattern). Raise `RuntimeError` after 3 failures.

3. Update `src/cv_maker/providers/__init__.py`:
   - Add import: `from cv_maker.providers.openai_provider import OpenAIProvider`
   - Add `"OpenAIProvider"` to `__all__`.
   - In `get_provider()`, add a branch BEFORE the default return: `if model == "openai": return OpenAIProvider()`.
   - Update the docstring to list the three supported values: "gemini-flash", "openai", "claude-haiku".

4. Update `backend/routers/config.py`:
   - Add `openai_available` to the returned dict: `"openai_available": bool(os.environ.get("OPENAI_API_KEY"))`.
   - Update the docstring to mention both Gemini and OpenAI availability.

5. Append to `.env`: three new lines: `OPENAI_API_KEY=`, `OPENAI_BASE_URL=`, `OPENAI_MODEL=gpt-4o-mini`.
  </action>
  <verify>
    <automated>cd /Users/nroo6394/Library/CloudStorage/OneDrive-SyscoCorporation/Documents/cv-maker && python -c "from cv_maker.providers.openai_provider import OpenAIProvider; print('Import OK')" && python -c "from cv_maker.providers import get_provider; p = get_provider('claude-haiku'); print(type(p).__name__)" && uv run python -c "import openai; print('openai', openai.__version__)"</automated>
  </verify>
  <done>OpenAIProvider class exists, imports cleanly, factory routes "openai" to it, config endpoint returns openai_available flag, openai package is in uv.lock</done>
</task>

<task type="auto">
  <name>Task 2: Extend ModelSelector UI with OpenAI toggle button</name>
  <files>frontend/src/components/ModelSelector.vue, frontend/src/views/JobFormView.vue</files>
  <action>
1. Update `frontend/src/components/ModelSelector.vue`:
   - Add `openaiAvailable: boolean` to the `defineProps` generic type (alongside existing `geminiAvailable`).
   - Add a third entry to the `options` array: `{ value: 'openai', label: 'OpenAI', hint: 'Works with any OpenAI-compatible API endpoint (Groq, Together AI, Ollama, etc.)' }`.
   - Update `select()` function: add a guard `if (model === 'openai' && !props.openaiAvailable) return` (matching the Gemini pattern).
   - Update `hintText()`: add a condition for OpenAI not configured: `if (props.modelValue === 'openai' && !props.openaiAvailable) return 'OpenAI requires OPENAI_API_KEY — not configured.'`
   - Update `isDisabledOption()`: return true also when `value === 'openai' && !props.openaiAvailable`.

2. Update `frontend/src/views/JobFormView.vue`:
   - Add `const openaiAvailable = ref(false)` alongside the existing `geminiAvailable`.
   - In the `onMounted` fetch callback, add: `openaiAvailable.value = data.openai_available === true`.
   - Update the `<ModelSelector>` template usage to pass the new prop: `:openai-available="openaiAvailable"`.
  </action>
  <verify>
    <automated>cd /Users/nroo6394/Library/CloudStorage/OneDrive-SyscoCorporation/Documents/cv-maker/frontend && npx vue-tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>ModelSelector shows three toggle buttons (Claude Haiku, Gemini Flash-Lite, OpenAI). OpenAI button is disabled when openaiAvailable is false, enabled when true. Hint text displays correctly for each model. vue-tsc passes with no type errors.</done>
</task>

</tasks>

<verification>
- `uv run python -c "from cv_maker.providers import get_provider, OpenAIProvider; p = get_provider('openai'); assert isinstance(p, OpenAIProvider)"` — factory routing works
- `uv run python -c "from cv_maker.providers import get_provider; p = get_provider('claude-haiku'); print(type(p).__name__)"` — default fallback unbroken
- `cd frontend && npx vue-tsc --noEmit` — no TypeScript errors
- `uv run pytest tests/ -x -q` — existing tests still pass
</verification>

<success_criteria>
- OpenAI provider class follows identical pattern to GeminiProvider (lazy init, 3-attempt retry, shared _build_prompt/_extract_json)
- Factory routes "openai" string to OpenAIProvider
- GET /api/config returns both gemini_available and openai_available flags
- ModelSelector has three toggle buttons with correct enable/disable gating
- All existing tests pass; no TypeScript errors
</success_criteria>

<output>
After completion, create `.planning/quick/260405-srf-add-openai-compatible-api-provider-as-th/260405-srf-SUMMARY.md`
</output>
