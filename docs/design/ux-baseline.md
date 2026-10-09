# CV Maker UX baseline (pre-redesign)

Observed from repository routes and a local build at desktop 1280×601 and mobile 390×844 using a temporary database. This is a product inspection, not user research. Screenshots used for inspection live outside the repository because the bundled base CV contains personal details.

## Workflow and strengths

- Job seekers enter company and job description on `/`, optionally link, notes, base CV, model and creativity; submit a job and move to `/jobs/:id` for progress, CV, cover letter, analysis, source listing, editing/regeneration and PDF.
- `/base-cv` manages profiles and editable CV sections; `/convert` can turn pasted/uploaded text into a base CV; `/settings` configures providers and output filename; `/signin` hosts Google sign-in.
- Existing sessions, profile access and settings stay close at hand in the sidebar. The input flow is direct, and status/error/retry handling already exists. Light and dark themes exist; key fields have labels.

## Specific friction observed

1. Desktop home uses a narrow plain form on a large flat dark canvas. Company and lengthy job description have similar visual priority, while the primary outcome and readiness requirements are not visible above the fold.
2. Settings and model choice are needed before generating, but the model controls can be disabled without an immediately prominent route to configuration. The empty sidebar says to submit a listing even when no provider is configured.
3. Mobile home is one very long uninterrupted form. The sidebar collapses, but field hierarchy and task framing do not improve; the model choice squeezes four labels into a single row.
4. Base-CV management starts with dense toolbar controls, prominent management chrome and an immediately expansive data editor. The currently selected base profile and its purpose can be clearer.
5. Import view currently describes `.txt` and pasted text, while the broader product offers PDF upload elsewhere; label the distinct paths accurately rather than implying unsupported formats.
6. Sign-in relies on Google Identity Services; if configuration or script availability fails, the central card can have no obvious action. This is an observed test-environment limitation, not a claim that production sign-in is broken.

## Working constraints

Keep current routes, controls, tabs, async statuses, editing and downloads. Do not turn a one-page submission into a wizard. Use restrained hierarchy, readable contrast, responsive spacing and accessible focus rather than decoration for its own sake. Browser review can use a disposable local database and development JWT; AI generation requires an externally configured provider and cannot be assumed available.
