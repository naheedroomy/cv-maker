# Quick Task 260406-jb6: Add creativity slider to control AI tailoring liberty - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Task Boundary

Add a creativity/fabrication level selector (0-5) to the job submission form. The value controls how much liberty the AI takes when tailoring the CV — from strict reordering to creative fabrication. The level is passed through the API, stored per job, and injected into the prompt.

</domain>

<decisions>
## Implementation Decisions

### Level Definitions (6 levels, 0-5)
- **0 - Strict**: Reorder only, zero content changes
- **1 - Conservative**: Emphasize and reframe existing content
- **2 - Moderate**: Current behavior — title tweaks, tech weaving, inferred experience (DEFAULT)
- **3 - Forward**: Expand partial matches aggressively, more inferred responsibilities
- **4 - Bold**: Fill gaps with plausible claims, speculative additions
- **5 - Creative**: Invent freely, maximize relevance at cost of accuracy

### UI Design
- Segmented pill buttons (same pattern as ModelSelector) showing numbers 0-5
- Descriptive hint text below that updates per selection
- Example: `[0] [1] [2] [3] [4] [5]` with hint "2 — Moderate: title tweaks, tech weaving, inferred experience"

### Default Level
- Default: 2 (Moderate) — matches current prompt behavior, existing users see no change

### Data Flow
- Frontend sends `creativity_level: int` (0-5) in POST /api/jobs body
- Stored in jobs table as integer column (default 2)
- Worker passes level to provider
- `_build_system_prompt()` receives level and adjusts instructions accordingly
- Each provider's `run()` method should accept and forward the level

</decisions>

<specifics>
## Specific Ideas

- New CreativitySlider.vue component mirroring ModelSelector.vue pattern
- Add `creativity_level` field to JobCreate schema and jobs table
- The prompt adjustment should be a block of text prepended/appended to the system prompt based on level
- Level 2 should produce identical prompt to current behavior (backward compatible)
- Levels 0-1 add restrictive instructions (e.g., "Do NOT change titles", "Do NOT add bullets")
- Levels 3-5 relax constraints and add permissive instructions (e.g., "You MAY invent plausible responsibilities")

</specifics>
