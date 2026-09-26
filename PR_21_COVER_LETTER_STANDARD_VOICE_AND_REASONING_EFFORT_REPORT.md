# PR #21 Report: Cover Letter Standard Engineering Voice & Reasoning Effort Integration

**Title:** Standardize Cover Letter Voice to Engineering Peer, Elevate Custom Instructions, and Wire AI Reasoning Effort Controls  
**Branch:** `feature/cover-letter-standard-voice-and-effort`  
**Base:** `master`  
**Files Modified/Deleted:**
- `core/cover_letter.py`
- `core/codemap.md`
- `backend/schemas.py`
- `backend/routers/cover_letter.py`
- `frontend/src/components/CoverLetterSection.vue`
- `frontend/src/components/ToneSelector.vue` *(deleted)*
- `frontend/src/components/codemap.md`
- `frontend/src/stores/jobStore.ts`
- `frontend/src/stores/codemap.md`
- `tests/test_cover_letter_prompt.py`

---

## 1. Executive Summary & Motivation

In previous iterations, the cover letter generation interface offered multiple tone options (*Formal*, *Professional*, *Confident*, *Direct*, *Casual*, *Enthusiastic*). In practice, fine-grained tone dropdowns often produced formulaic or artificial variations, while candidates still needed a clear way to provide custom constraints (e.g., word count limits, specific projects to emphasize, relocation context).

Furthermore, while the primary CV tailoring pipeline allowed users to configure AI model variants and reasoning effort levels (*low*, *medium*, *high*, *auto*) via `ModelSelector.vue`, cover letter generation lacked UI controls to choose reasoning effort or model overrides.

### Core Objectives Achieved in PR #21:
1. **Single Standard Voice**: Unified all generation under one high-signal, natural style: the **respected engineering peer** voice (balanced, credible, articulate, collegial, conversational, with natural contractions and active verbs).
2. **Prioritized Custom Instructions**: Repositioned the custom instructions & notes textbox as the primary customization lever for candidate-directed constraints, relocation details, and narrative emphasis.
3. **Reasoning Effort & Model Variant Controls**: Enabled full `ModelSelector` capabilities in `CoverLetterSection.vue` with `:show-model-details="true"`, allowing users to adjust reasoning effort and model variants directly when generating or regenerating cover letters.
4. **Clean Backward Compatibility**: Mapped legacy tone requests (`professional`, `casual`, `formal`, etc.) to the standard voice and kept database column compatibility without migrations.

---

## 2. Key Architecture & Code Changes

### A. Core Engine (`core/cover_letter.py`)
- **Standard Voice Instruction**:
  ```python
  _STANDARD_TONE_INSTRUCTION = (
      "Write as a respected engineering peer: balanced, credible, articulate, and collegial. "
      "Sound like a thoughtful colleague writing an introductory note to a team they would love "
      "to work with. Use natural professional greetings ('Hi [Name/Team],' or "
      "'Dear [Name/Hiring Team],') and clean closings ('Best regards,' or 'Best,'). "
      "Natural contractions, conversational rhythm, clear active verbs, and zero corporate posturing."
  )
  ```
- **Legacy Aliases**: Mapped `_TONE_INSTRUCTIONS["standard"]` and all legacy tones (`"professional"`, `"casual"`, `"confident"`, `"direct"`, `"enthusiastic"`, `"formal"`) to `_STANDARD_TONE_INSTRUCTION`.
- **System Prompt Calibration**: Updated `SYSTEM_PROMPT_TEMPLATE` to explicitly prioritize candidate custom instructions provided in `USER NOTES`:
  ```
  VOICE & TONE PRECEDENCE:
  - If the candidate provides custom instructions or notes in USER NOTES (e.g., constraints,
    specific projects to emphasize, relocation context, or nuances), prioritize them while keeping
    all claims strictly grounded in the candidate's verified background.
  - If a candidate writing sample is provided, use it to calibrate natural stylistic rhythm,
    sentence variety, and vocabulary cadence. The standard peer voice strictly governs the
    social register, greeting, and sign-off.
  - Otherwise, maintain the standard professional engineering peer voice throughout.
  ```
- **Function Defaults**: Updated `generate_cover_letter` default parameter to `tone: str = "standard"`.

### B. Backend Schema & Router (`backend/schemas.py`, `backend/routers/cover_letter.py`)
- In `backend/schemas.py`:
  - Updated `CoverLetterRequest.tone` to default to `"standard"`.
  - Removed restrictive regex pattern `^(formal|professional|...)$` so `"standard"` and any legacy strings validate cleanly without 422 errors.
- In `backend/routers/cover_letter.py`:
  - Defaulted `tone="standard"` in `_cover_letter_worker`.
  - Formatted SQL statements and route signatures to comply strictly with the project's 100-character line-length rule (`uv run ruff check`).

### C. Frontend State & UI (`frontend/src/`)
- **Store Action (`jobStore.ts`)**:
  - Updated `generateCoverLetter(jobId, model, userNotes, modelId?, reasoningEffort?)` signature.
  - Included `model_id` and `reasoning_effort` in the POST request body.
- **Component (`CoverLetterSection.vue`)**:
  - Removed `ToneSelector.vue` import and component tag.
  - Bound `v-model:model-id="selectedModelId"` and `v-model:reasoning-effort="selectedReasoningEffort"` with `:show-model-details="true"` on `ModelSelector`.
  - Formatted the form layout logically:
    1. `ModelSelector` (AI provider pills + variant dropdown + reasoning effort pills).
    2. `Custom instructions & notes (optional)` textarea with expanded placeholder guidance.
    3. `Generate Cover Letter` button.
  - Formatted history items and metadata badges so `"standard"` tone is clean while legacy versions with non-standard tones remain legible.
- **Deleted Dead Component**: Removed `ToneSelector.vue`.

---

## 3. Verification & Test Evidence

### A. Python Automated Test Suite (`uv run pytest`)
- Run output: **262 passed, 5 skipped** (100% pass rate).
- Added comprehensive unit tests in `tests/test_cover_letter_prompt.py`:
  - `test_all_expected_tones_are_registered`: Verifies `"standard"` and legacy tone compatibility.
  - `test_system_prompt_prioritizes_custom_instructions_in_user_notes`: Validates prompt instruction hierarchy.
  - `test_cover_letter_request_schema_defaults`: Validates Pydantic schema default values for `tone="standard"`, `reasoning_effort`, and `model_id`.
  - `test_generate_cover_letter_mock_provider`: Validates default generation execution without explicit tone parameter.

### B. Python Linter (`uv run ruff check`)
- All modified and related files checked:
  - `core/cover_letter.py` → **All checks passed (0 errors)**.
  - `backend/schemas.py` → **All checks passed (0 errors)**.
  - `backend/routers/cover_letter.py` → **All checks passed (0 errors)**.
  - `tests/test_cover_letter_prompt.py` → **All checks passed (0 errors)**.

### C. Frontend Build & Typecheck (`npm run build`)
- Executed `vue-tsc --build && vite build` in `frontend/`:
  - Output: **Built successfully in 180–210ms with 0 type errors**.
