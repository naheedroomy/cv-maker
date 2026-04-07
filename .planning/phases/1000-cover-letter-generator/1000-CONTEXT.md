# Phase 1000: Cover Letter Generator - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate tailored cover letters using the base CV, job listing, and tailored CV output. Cover letters sound human via humanizer-inspired anti-AI-smell rules and a two-pass generate-then-self-critique architecture. Users can add free-text notes to weave into the letter. Output is an editable text box with copy-to-clipboard and PDF download.

</domain>

<decisions>
## Implementation Decisions

### D-01: Generation Trigger
- On-demand button on JobDetailView after CV generation completes
- "Generate Cover Letter" button appears in a new Cover Letter section below the tailored CV and gap analysis
- Clicking reveals a notes textarea + tone selector + generate button
- After generation: editable text preview with copy + "Save & Download PDF"

### D-02: Output Format
- Primary: editable text box in the browser (user can tweak before saving)
- Copy-to-clipboard button for pasting into applications/emails
- "Save & Download PDF" button — simple text-to-PDF (no LaTeX needed, just clean formatted text)
- Cover letter stored in the database per job (alongside tailored_cv and gap_diff)

### D-03: User Notes UX
- Free-text textarea (optional) above the generate button
- User types anything: "mention I'm relocating to Berlin", "highlight the K8s migration project", "I know someone at this company"
- The prompt interprets and weaves notes naturally — no structured fields
- Notes stored per cover letter generation for regeneration context

### D-04: Tone Selector
- Separate 4-option segmented pill selector, independent from CV creativity slider
- Options: **Formal** / **Professional** / **Confident** / **Casual**
  - Formal: traditional corporate ("I am writing to express my interest...")
  - Professional: direct, no fluff ("Your role aligns with my 4 years of K8s experience.")
  - Confident: assertive, specific ("I built a self-healing K8s platform that cut MTTR from 60 to 5 min.")
  - Casual: conversational, shows personality
- Default: Professional
- New ToneSelector.vue component (same pattern as ModelSelector pills)

### D-05: Anti-AI-Smell Rules (from humanizer research)
Baked into the cover letter prompt (not user-facing):
1. No significance inflation ("pivotal", "testament to", "underscores")
2. No promotional language ("passionate about", "thrilled to apply", "committed to excellence")
3. Simple verbs — "I connect X and Y" not "I serve as the bridge between"
4. No rule-of-three clusters ("innovation, collaboration, and impact")
5. No generic conclusions ("I look forward to the opportunity to discuss further")
6. No -ing participial padding ("leveraging", "contributing to", "fostering")
7. No filler ("In order to" → "To", "I have the ability to" → "I can")
8. Vary sentence rhythm — mix short punchy with longer sentences
9. Have opinions, don't hedge — "I can" not "I could potentially be"
10. Specificity over scope — concrete facts, not broad claims

### D-06: Two-Pass Architecture
- Pass 1: Generate cover letter draft
- Pass 2: Self-critique — ask the model "What makes this still obviously AI-generated?" and revise
- Both passes in a single API call (system prompt instructs the two-pass approach internally)

### D-07: Provider and Data Flow
- Reuse existing provider abstraction (all 4 providers via get_provider)
- Inputs: base_cv + job_text + tailored_cv JSON + gap_diff + user_notes + tone
- New API endpoint: POST /api/jobs/:id/cover-letter (generates cover letter for an existing completed job)
- New DB column: cover_letter_text (nullable, on jobs table)
- Cover letter generation is a separate call from CV generation — not part of the main pipeline

### Claude's Discretion
- PDF styling (font, margins, spacing) — keep it clean and professional
- Cover letter length — typical 3-4 paragraphs, let the model decide based on content
- How to handle regeneration — likely reuse RegeneratePanel pattern with tone selector

</decisions>

<canonical_refs>
## Canonical References

### Humanizer Anti-AI Patterns
- `/Users/nroo6394/Library/CloudStorage/OneDrive-SyscoCorporation/Documents/humanizer/SKILL.md` — Full 29-pattern reference for anti-AI writing rules. Distilled to 10 rules in D-05.

### Existing Provider Pattern
- `src/cv_maker/providers/base.py` — BaseProvider ABC, .run() interface
- `src/cv_maker/providers/__init__.py` — get_provider() factory
- `src/cv_maker/pipeline.py` — _RULES dict, parameterized prompt builder pattern

### Existing UI Components
- `frontend/src/components/ModelSelector.vue` — Pill selector pattern to follow for ToneSelector
- `frontend/src/components/CreativitySlider.vue` — Numbered pill pattern
- `frontend/src/components/RegeneratePanel.vue` — Expandable panel pattern
- `frontend/src/views/JobDetailView.vue` — Where cover letter section will be added

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Provider abstraction (BaseProvider, get_provider) — reuse for cover letter generation
- ModelSelector.vue — clone pattern for ToneSelector.vue
- RegeneratePanel.vue — reuse pattern for cover letter regeneration
- Worker job queue — may need cover letter as a lightweight second pass or separate endpoint
- CvPreview.vue — reference for text preview layout

### Established Patterns
- Pydantic models for API request/response contracts (backend/schemas.py)
- asyncio.to_thread for blocking provider calls
- SSE for real-time status updates (may not be needed for cover letter — it's a fast single call)
- Settings cache for configurable values

### Integration Points
- JobDetailView.vue — add cover letter section below existing content
- jobs router — add POST /api/jobs/:id/cover-letter endpoint
- jobs table — add cover_letter_text column (nullable, idempotent migration)
- worker.py or new cover_letter_worker — generate cover letter via provider

</code_context>

<specifics>
## Specific Ideas

- The editable text box is key — user should be able to tweak the cover letter before downloading
- PDF doesn't need LaTeX — simple formatted text-to-PDF (could use Playwright or even just a styled HTML page rendered to PDF)
- Cover letter should reference specific achievements from the tailored CV — the gap analysis tells it what to emphasize
- The two-pass approach should be transparent: the model generates, then critiques and revises in the same call
- Work on feature/cover-letter branch, not master

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 1000-cover-letter-generator*
*Context gathered: 2026-04-07*
