# PR #16 follow-up: evidence and prompt-safety review

**Companion to:** [PR_16_ATS_PROMPT_UPGRADE_REPORT.md](PR_16_ATS_PROMPT_UPGRADE_REPORT.md)  
**Reviewed implementation:** merge commit `22d24b7` (`core/pipeline.py`, `tests/test_pipeline.py`)  
**Status:** Review and recommendations only; no prompt changes are implemented by this document.

## Decision

Keep the direction of PR #16—specific, relevant, evidence-backed CV writing—but **do not describe it as proven ATS score optimization or a guarantee against fabrication**. The current tests prove that prompt fragments are present, not that generated CVs are accurate or more successful. Fix the prompt contradictions and unsafe example before claiming quality improvements.

## Findings and required changes

| Priority | Finding | Evidence | Change and acceptance criterion |
| --- | --- | --- | --- |
| P0 | The new style example teaches unsupported embellishment. The “before” establishes Terraform in development and production; the “after” adds multi-AZ VPCs, EKS, modularity, and eliminated drift. | `core/pipeline.py:742–748`; original report §3.7. | Replace it with a before/base-evidence/after example. **Every new technical noun and outcome in “after” must be traceable to the displayed base evidence.** Use a modest rewrite if none is available. Apply the same fix in both CLI and chat prompts. |
| P0 | “Zero fabrication risk” is false. Technical scope can be invented without a number; the validator warns rather than fails on invented metrics, and creativity level 6 allows fabrication. | `core/pipeline.py:515,1167–1168`; `core/validation.py:106–148,285`; original report §6. | Say “reduces risk through prompt guidance; candidate review remains required.” Do not present a list of impressive scopes as a fallback unless each is verified for that role. Decide separately whether level 6 and validator policy should change; this PR does not resolve them. |
| P1 | Latest-role keyword density is a fixed quota based on an undocumented scoring assertion. It can reward moving old experience into a recent role, conflicting with the role-level evidence rule. | `core/pipeline.py:582–588,605–615`; original report §§2, 3.5. | Remove “60–70%” and the assertion of temporal ATS scoring. Prefer recent **verified** evidence when relevant, but preserve the real role and dates. Test a CV whose best-matched technology occurs only in an older role. |
| P1 | The audit requests bolding tools in the summary while three prompt paths prohibit summary bolding. It is a self-check instruction, not an enforced gate; the staged generator has no equivalent newly added audit/example. | `core/pipeline.py:712,802–808,921,989,1554–1578`; `core/providers/claude_api_provider.py:132`. | Choose one summary rule (recommend **no bold in summary**), apply it consistently, and describe this as a prompt self-check unless validated after generation. Ensure all supported provider paths receive equivalent safety guidance. |
| P1 | The report claims vendor-specific score gains, keyword penalties, and **3×** recency weighting without a scoring specification or comparative results. Ashby says its AI does not assign numerical applicant rankings. | Original report §§1–2, 6; [Ashby AI](https://www.ashbyhq.com/ai); [Textkernel parser data model](https://developer.textkernel.com/Parser/master/data_model/candidate-data-model/). | Distinguish semantic/skills matching **capabilities** from unproven scoring mechanics. Remove predictions that Ashby, Eightfold, or Workday “will award higher relevance scores.” |
| P2 | The “three-sentence” summary and universal anti-AI screening claims are overstated. The rule permits 2–4 sentences at levels 2–3 and differs at levels 0–1; no rejection-rate evidence is supplied for particular verbs or punctuation. | `core/pipeline.py:260–309,315–338`; original report §§1, 3.2–3.3. | Describe 2–4 sentences at levels 2–3. Prefer concrete verbs and cut generic qualifiers without claiming that a single banned verb triggers rejection. Treat Google XYZ as an optional structure, not a demand to invent [Y]. |
| P2 | New tests inspect strings, not generated CVs or hiring outcomes. | `tests/test_pipeline.py:1417–1480`; original report §§5–6. | Add output-level cases and an evidence-linked human evaluation before reporting quality or match-rate improvements. |

## Suggested replacement for the report's outcome claims

> PR #16 adds prompt guidance for context-rich, relevant, evidence-backed CV bullets and reduces generic phrasing. Automated tests confirm the instructions appear in selected prompt builders. We have **not** measured improvements in ATS scores, screening decisions, or recruiter preference. Prompt instructions cannot guarantee factual accuracy: the candidate should verify every changed accomplishment, technology, and scope against the base CV before applying.

For the industry section, use: “Some recruitment products support skills extraction or semantic matching. Their scoring, configuration, and use of human review differ; this project has not tested vendor-specific ranking behaviour.”

## Verification plan for a follow-up implementation

1. Build a small consent-safe fixture set: base CV, job description, role-level evidence, expected allowable claims, and at least one case with a relevant skill **only in an older role**. Include cases with no metrics and with a bare Terraform mention but no EKS/multi-AZ evidence.
2. Unit-test the assembled **CLI, chat, and staged** prompts for consistent truth, recency, and summary-format rules; assert that the unsafe Terraform example and 60–70% quota are absent.
3. Capture generated CVs with pinned provider/model/settings. Review before/after outputs blind for unsupported metrics **and non-numeric scope**, role misplacement, omitted relevant evidence, readability, and keyword coverage. Treat any invented claim as a failure; do not infer ATS success from string-presence tests.
4. If claiming ATS gains later, define the actual vendor/configuration, test method, comparison baseline, sample size, and measured outcome. Without those, report only observed output quality.

**Local verification at review:** `uv run pytest -q` → **248 passed, 5 skipped**; `cd frontend && npm run build` → passed. `uv run ruff check .` → **236 existing working-tree findings in total**; this review did not attribute those findings to PR #16. The new prompt tests should not be characterized as outcome or ATS integration tests.

**Next step:** implement the P0/P1 prompt changes, run the three prompt-path checks and output evaluation, then revise the original report to distinguish implemented behaviour from hypotheses.
