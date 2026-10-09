# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: job seekers tailoring a CV to a specific vacancy, often trying to move from a job description to an application-ready document without extra steps. The owner confirmed that their needs take precedence over high-volume power-user density or a personal-only workflow. Time pressure and device constraints are plausible design assumptions, not user research.

## Product Purpose

CV Maker helps a job seeker prepare and maintain one or more base CVs, tailor a CV against a job listing using a configured AI provider, inspect the result and gap analysis, edit or regenerate it, download a PDF, and optionally draft a cover letter. A successful session preserves a simple create → review → download path and leaves the user able to inspect and correct claims.

## Operating Context

Existing Vue 3 web SPA routes: sign-in, job submission, job detail (CV, cover letter, analysis, listing), base-CV manager, text-to-CV conversion, and provider settings. Signed-in users navigate job sessions in a sidebar; the app has light/dark themes. Generation is asynchronous, with progress, cancellation, failure and retry states. A base CV can be uploaded from PDF or edited manually; job input requires company name and description. Provider availability and user keys are configured in Settings.

## Capabilities and Constraints

- Existing API contracts, routes, auth, stored data, CV-generation behavior, and document capabilities must remain intact through redesign.
- Keep the direct job-submission-to-result workflow, without extra mandatory steps or visual distractions.
- Product is a utility, not an engagement experience: clear states and reversible editing where supported matter more than time spent or ornamental interactions.
- There is no confirmed commercial model, user research, launch date, logo, or external brand system; do not fabricate them.

## Brand Commitments

The product name is CV Maker. The owner confirmed simplicity of workflow, not preservation of current colors, type, or visual branding.

## Evidence on Hand

Repository implementation and copy in `frontend/src/`, routing in `frontend/src/router/index.ts`, and documented functionality in `codemap.md` and local codemaps. There are no known validated usability results, testimonials, performance claims, or approved marketing assets.

## Product Principles

1. Make the next step apparent: job description in, tailored CV out, with optional controls secondary.
2. Preserve applicant agency: generated content remains inspectable, editable and downloadable; no overstated promises.
3. Reveal relevant controls and feedback when needed rather than forcing users through additional stages.
4. Design for busy job seekers across desktop and mobile, with usable keyboard navigation and clear error recovery.

## Accessibility & Inclusion

Redesign acceptance requires keyboard and screen-reader basics, readable contrast and reduced-motion support. No specific disability research or additional regulatory standard has been established.
