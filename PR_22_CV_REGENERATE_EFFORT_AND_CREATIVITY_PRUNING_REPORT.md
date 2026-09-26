# PR #22 Report: CV Regeneration Controls, Reasoning Effort & Creativity Level Pruning (0–3)

**Title:** Wire Model Overrides, Reasoning Effort, and Custom Instructions to CV Regeneration; Prune Creativity Levels to 0–3 (Strict to Selective)  
**Branch:** `feature/cv-regenerate-effort-and-creativity-pruning`  
**Base:** `master`  
**Files Modified:**
- `core/pipeline.py`
- `core/codemap.md`
- `backend/schemas.py`
- `backend/routers/jobs.py`
- `backend/routers/codemap.md`
- `frontend/src/types.ts`
- `frontend/src/components/CreativitySlider.vue`
- `frontend/src/components/RegeneratePanel.vue`
- `frontend/src/components/codemap.md`
- `frontend/src/views/JobDetailView.vue`
- `frontend/src/stores/codemap.md`
- `frontend/src/assets/codemap.md`
- `tests/test_pipeline.py`
- `tests/test_jobs_router.py`

---

## 1. Executive Summary & Motivation

Previously, when users created an initial tailored CV via `JobFormView.vue`, they had granular controls over:
- The base provider model (`Claude API`, `Gemini`, `OpenAI`, `Gemini Web`).
- Custom model IDs (e.g. `claude-3-7-sonnet-20250219`, `gemini-2.5-pro`, `o3-mini`).
- Reasoning effort settings (`low`, `medium`, `high`, `auto`).
- Custom instructions / generation notes (e.g. *"replace GCP with AWS on HiAcuity work experience"*).

However, during CV **regeneration** on existing jobs via `RegeneratePanel.vue`:
1. The UI only displayed the basic model provider buttons and the creativity slider. The model details section (custom model ID, reasoning effort) was hidden (`:show-model-details` was not active).
2. The user had no textbox to provide regeneration instructions (such as swapping stacks, highlighting specific projects, or revising emphasis).
3. The creativity slider had 7 levels (0 through 6). Levels 4, 5, and 6 historically included soft-fabrication and speculative technology exposure that violated factual ATS grounding. In practice, users only needed safe tailoring ranges (Strict, Conservative, Balanced, Selective) paired with specific user instructions for targeted revisions.

### Core Objectives Achieved in PR #22:
1. **Model Overrides & Reasoning Effort in Regeneration**: Full support for `ModelSelector` with `:show-model-details="true"`, allowing users to select model IDs and reasoning effort on CV regeneration.
2. **Custom Instructions & Notes Textbox**: Added a dedicated instructions textarea in `RegeneratePanel.vue`, initialized with the current job's `user_notes` (if any), enabling targeted edits like *"replace GCP with AWS on HiAcuity work experience"*.
3. **Pruned Creativity Levels (0–3)**: Kept levels 0 through 3 (`0: Strict`, `1: Conservative`, `2: Balanced`, `3: Selective`) and completely pruned levels 4, 5, and 6 from the core engine, backend schemas, and UI.
4. **Resilient Backward Compatibility**: Added clamping `max(0, min(3, raw_creativity))` in the backend router so historical database jobs created with levels 4–6 regenerate gracefully without 500/422 errors.

---

## 2. Key Architecture & Code Changes

### A. Core Engine (`core/pipeline.py`)
- **`Creativity` IntEnum**: Pruned enum values:
  ```python
  class Creativity(IntEnum):
      STRICT = 0
      CONSERVATIVE = 1
      DEFAULT = 2
      SELECTIVE = 3
  ```
- **Rule Pruning**: Pruned `_RULES` dictionary across `titles`, `bullets`, `skills_injection`, `summary`, and `substitution` to remove all entries for levels 4, 5, and 6. Level 3 retains limited stack substitution (at most 1 role, no new bullets, truthful guardrails).
- **Prompt Clamping**: Updated all builders (`_build_prompt`, `_build_system_prompt_for_chat`, `map_evidence`, `generate_tailored_cv`) from `max(0, min(6, ...))` to `max(0, min(3, ...))`.

### B. Backend Schemas & Router (`backend/schemas.py`, `backend/routers/jobs.py`)
- **Validation**: Updated `JobCreateRequest.creativity_level` and `RegenerateRequest.creativity_level` to `Field(ge=0, le=3)`.
- **Legacy Row Clamping**: When regenerating without supplying an explicit `creativity_level`, the router retrieves the existing job's `creativity_level` and clamps it via `max(0, min(3, raw_creativity))`.
- **Payload Forwarding**: Full propagation of `model_id`, `reasoning_effort`, and `user_notes` into DB updates and worker tasks.

### C. Frontend Components & Views
- **`CreativitySlider.vue`**:
  - Pruned levels array to:
    - `0`: Strict ("Reorder only. Never change titles, technologies, or bullet text.")
    - `1`: Conservative ("Light phrasing polish. No technology changes or additions.")
    - `2`: Balanced ("Default. Modest bullet rewrites, infers standard tools from experience.")
    - `3`: Selective ("Limited stack substitution on at most 1 older role.")
  - Removed outdated warning classes.
- **`RegeneratePanel.vue`**:
  - Bound `:show-model-details="true"` to `ModelSelector` with `v-model:model-id` and `v-model:reasoning-effort`.
  - Added Custom Instructions textarea with placeholder:
    `"Custom instructions (e.g. emphasize platform engineering, replace GCP with AWS on HiAcuity, highlight distributed systems)..."`
  - Emits `(model, creativityLevel, userNotes, modelId, reasoningEffort)`.
  - Resets state cleanly when navigating between jobs.
- **`JobDetailView.vue`**:
  - Passes `:current-notes="currentJob.user_notes"`, `:current-model-id="currentJob.model_id"`, and `:current-reasoning-effort="currentJob.reasoning_effort"` into `RegeneratePanel`.
  - Updated `handleRegenerate` to pass all 5 arguments to `store.regenerateJob`.

---

## 3. Verification & Test Results

### A. Python Backend & Core Tests (`uv run pytest`)
- **263 passed, 5 skipped, 0 failures** in 0.89s.
- Key new tests added to `tests/test_jobs_router.py`:
  - `test_regenerate_job_with_effort_model_and_notes`: Verifies passing model override, effort level, and custom instructions updates the job row in the database and returns them in the response.
  - `test_regenerate_job_legacy_creativity_clamped`: Verifies older jobs with `creativity_level=5` in the DB clamp to `3` upon regeneration.
  - `test_job_create_and_regenerate_creativity_validation`: Verifies `creativity_level > 3` is rejected with 422 Unprocessable Entity for both creation and regeneration.
- Updated `tests/test_pipeline.py`:
  - Clamping test verified for 0–3 range.
  - Keyword and bullet strategy tests verified across all 4 valid levels (0–3).
  - Distinct prompts test verified across 0–3.

### B. TypeScript & Frontend Verification (`npm run build`)
- `vue-tsc --build` completed with **0 type errors**.
- Vite production build bundled cleanly in 167ms.
