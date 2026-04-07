# Phase 1000: Cover Letter Generator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 1000-cover-letter-generator
**Areas discussed:** Generation trigger, Output format, User notes UX, Tone & personality

---

## Generation Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| On-demand button | Button on JobDetailView after CV completes. Notes textarea + generate. | ✓ |
| Automatic with CV | Generated as part of same pipeline. No extra click but no notes input. | |
| Separate page | Entirely separate form/route. More isolated but more clicks. | |

**User's choice:** On-demand button
**Notes:** Appears below CV preview and gap analysis. Clicking reveals notes + tone + generate.

---

## Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| Plain text + copy | Cover letters usually pasted. Plain text with copy button. | |
| LaTeX PDF | Formal PDF with matching CV styling. Overkill for most use cases. | |
| Both options | Plain text default + optional PDF download. | ✓ |

**User's choice:** Both options
**Notes:** "Should show the copy button but also generate a PDF. This PDF need not be LaTeX — just text. Show cover letter in a text box and allow edits before having a 'Save and Download PDF' button."

---

## User Notes UX

| Option | Description | Selected |
|--------|-------------|----------|
| Free-text textarea | Simple textarea, user types anything. Prompt interprets naturally. | ✓ |
| Structured bullet inputs | Add/remove tagged fields (mention, emphasize, context). | |
| You decide | Claude's discretion. | |

**User's choice:** Free-text textarea
**Notes:** Lowest friction approach. User types freeform instructions.

---

## Tone & Personality

| Option | Description | Selected |
|--------|-------------|----------|
| Creativity slider controls it | Reuse existing 0-5 slider for tone. | |
| Separate tone selector | New pills for cover letter tone, independent from CV slider. | ✓ |
| Fixed professional tone | Always professional. No choice. | |

**User's choice:** Separate tone selector

**Follow-up: Tone options**

| Option | Description | Selected |
|--------|-------------|----------|
| 3 options | Formal / Professional / Conversational | |
| 4 options | Formal / Professional / Confident / Casual | ✓ |
| You decide | Claude's discretion | |

**User's choice:** 4 options (Formal / Professional / Confident / Casual)

---

## Claude's Discretion

- PDF styling (font, margins, spacing)
- Cover letter length (typical 3-4 paragraphs)
- Regeneration UX pattern

## Deferred Ideas

None
