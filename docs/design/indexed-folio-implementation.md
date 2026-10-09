# Indexed Folio: implementation and visual review

**Direction approved:** Indexed Folio. **Audience:** job seekers preparing one application at a time. **Scope:** frontend only; the existing routes, API contracts, data, generation pipeline, editing, export and authentication logic are unchanged. Product assumptions and the pre-redesign inspection are recorded in `PRODUCT.md` and [`ux-baseline.md`](ux-baseline.md). This is an implementation review, not user research.

## Before → after

| Before | After | Why |
| --- | --- | --- |
| Flat dashboard form on an expansive canvas | A numbered **brief** alongside a compact **setup** sheet on desktop; same content stacked on mobile | Establishes the job listing as source material and keeps the next action visible without a wizard. |
| Sidebar sessions, management links and profile mixed in one rail | Indexed workspace actions, searchable application rows, source CV and account in distinct groups | Distinguishes “start an application” from “find an old one” and keeps task context available. |
| Dense result controls and unframed content | An application header, artifact tabs, actions and separate CV proof sections | Clarifies where the generated content is and where to review or revise it; no content or action was removed. |
| Base CV opens as an unframed editor | Source-file heading, active profile cue and the same collapsible editor | Makes the document of record explicit without hiding any editable fields. |
| Model choices and settings could be hard to locate on mobile | Two-row provider grid in Settings, a provider-required message and route from a disabled Generate action | Makes a prerequisite actionable instead of allowing a submission destined to fail. |
| Generic sign-in and import layout | Distinctive but restrained entry and source-import pages | Keeps onboarding and utility pages in the same system; no invented productivity promises. |

## Visual system

- **Concept:** an open work folio, not a dashboard or a literal paper simulation. Narrow evergreen task rail, pale mineral canvas, cream work surfaces, quiet hairlines, small indexed overlines and a precise citron marker for active state.
- **Type:** locally hosted variable Archivo; compact uppercase metadata and strong, close-set headings. Body remains conventional sentence case for readability. There is no external font fetch at runtime. Archivo's [SIL Open Font License](../../frontend/public/fonts/OFL.txt) is shipped alongside the built assets.
- **Tokens:** shared surfaces, borders, text and status colors live in `frontend/src/App.vue`. The rail scopes its darker palette inside `AppSidebar.vue`; light and dark themes share structure. Citron action text remains dark in both themes. Secondary and tertiary copy are calibrated for contrast rather than low-opacity decoration.
- **Composition:** maximum-width main content; wide brief + sticky setup at desktop sizes, one column below 980px, mobile navigation drawer below 900px. Input and output use the same header/index vocabulary.
- **States:** provider configuration failures lead to Settings; generation still uses the existing pending/running/complete/failed/cancelled lifecycle. Cancelled result offers regeneration. Buttons, fields, route links and the skip link have visible keyboard focus; the mobile drawer closes on Escape and route change; reduced-motion media preference removes animation. Artifact selectors are groups of toggle buttons with `aria-pressed` and descriptive labels.

## Browser evidence

These captures use **synthetic application/CV data and intercepted local API responses**, not a live Google account or a real AI provider. They demonstrate UI, responsiveness and local navigation; they do not establish live sign-in, model generation or PDF service behavior.

| Surface | Capture |
| --- | --- |
| Sign-in / configuration-error state (desktop light) | [sign-in](screenshots/signin-desktop.png) |
| Sign-in / configuration-error state (dark desktop and mobile) | [desktop](screenshots/signin-desktop-dark.png) · [mobile](screenshots/signin-mobile-dark.png) |
| Job entry (desktop) | [create](screenshots/create-desktop.png) |
| Job entry (mobile light) | [create mobile](screenshots/create-mobile.png) |
| Job entry (mobile dark) | [create dark](screenshots/create-mobile-dark.png) |
| Generated result (desktop) | [result](screenshots/result-desktop.png) |
| Generated result (mobile) | [result mobile](screenshots/result-mobile.png) |
| Base CV (mobile) | [base CV](screenshots/base-cv-mobile.png) |
| Settings (mobile dark) | [settings](screenshots/settings-mobile-dark.png) |
| Pending and running generation (dark) | [pending desktop](screenshots/status-pending-desktop.png) · [pending mobile](screenshots/status-pending-mobile.png) · [running desktop](screenshots/status-running-desktop.png) · [running mobile](screenshots/status-running-mobile.png) |
| Failed and cancelled generation (dark) | [failed desktop](screenshots/status-failed-desktop.png) · [failed mobile](screenshots/status-failed-mobile.png) · [cancelled desktop](screenshots/status-cancelled-desktop.png) · [cancelled mobile](screenshots/status-cancelled-mobile.png) |

Browser exercised at 1280×800 and 390×844: entry, a filled create→result submission through an intercepted API, CV/result actions and route navigation, base CV, import, settings, light/dark switch, drawer Escape/route closure, and zero horizontal overflow on the six routes at mobile width. Pending, running, failed and cancelled job states were each inspected and captured at both viewport sizes with intercepted status responses; each showed its message and available action. The failed-state **Try again** transitioned to pending, and a pending job's **Cancel Job** transitioned to cancelled. Settings and result tabs were adjusted from clipped horizontal rows to two-row grids after inspection. A first mobile result pass prompted reducing vertical card spacing; a contrast pass corrected dark-mode action labels and session status chips. The signed-out story-panel palette was made theme-independent; measured dark-mode text contrast against its background is 12.13:1 for the headline, 9.73:1 for body, and 10.32:1 for the citron index.

## Verification and limits

- `cd frontend && npm run build` runs type-check and Vite production build.
- `uv run pytest -q`: 281 passed, 13 existing warnings (SWIG deprecations and short test JWT keys). No frontend test harness is configured in this repository.
- `git diff --check` checks patch whitespace. The repository-wide `uv run ruff check .` still fails on pre-existing Python files (e.g. `core/pipeline.py`, `core/validation.py`, and tests); this frontend-only redesign changes no Python files. This is a baseline lint issue, not evidence that lint passed.
- The current mock cannot verify a Google Identity Services sign-in, real provider generation, server PDF export, or email/credential handling. The sign-in screenshot intentionally shows the configuration-error state of the local backend rather than pretending a Google login succeeded. These require a configured live environment and credentials and were not silently substituted.
- No claim of a measured usability improvement is made. The changes address specific inspection findings; user validation would be a separate activity.
