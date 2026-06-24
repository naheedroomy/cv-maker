## Context

Three prior changes have shaped the pipeline: `natural-keyword-evidence-pipeline` (keyword policy, multi-stage pipeline, keyword-stuffing validation), `impact-differentiator-bullet-strategy` (bullet strategy, generic-bullet validation, differentiator fields), and a review-fix pass. The infrastructure is stable: `_RULES` dict with creativity-level thresholds, three prompt builders (single-shot, chat system, Stage 3), `EvidenceMatch`/`EvidenceMap` intermediate models, and `validate_tailored_cv()` with soft-warning pattern.

This change addresses recruiter plausibility — the gap between keyword-optimized output and what reads as genuine, evidence-grounded experience. It adds prompt rules for truthful placement, validation for common plausibility failures (wrong-role keywords, awkward chains, JD mimicry), optional placement fields on `EvidenceMatch` to guide truthful keyword distribution, and deterministic technology bolding for consistent PDF output.

Constraints (unchanged):
- No contact/date/company/education/cert/language changes
- Role structure preserved
- No event-loop blocking, provider lazy imports, per-user keys
- No UI scope, no external dependencies

## Goals / Non-Goals

**Goals:**
1. Add `"recruiter_plausibility"` prompt rule covering truthful placement, natural language, bullet preservation, and placement distinction (experience/skills/omit).
2. Add `placement` and `placement_reason` string fields to `EvidenceMatch` (immutable defaults, no `Field(default_factory)` needed).
3. Extend Stage 2 prompt to request placement fields.
4. Add placement validation: wrong-role keywords, awkward chains, JD mimicry, highlighted-tech references, role-tech consistency, core-competencies tool leakage.
5. Add `apply_tech_bolding()` for deterministic `**bold**` normalization.
6. Update `core_competencies` / `highlighted_technologies` prompt distinction.
7. Add tests for all new behavior.

**Non-Goals:**
- No UI, frontend, backend route, database, Docker, or CI/CD changes.
- No new external dependencies.
- No breaking changes to existing models or provider interface.
- No changes to LaTeX templates — bolding produces standard `**markdown**` that the existing renderer already handles.

## Decisions

### Decision 1: Plausibility rule at level 0 in `_RULES`

**Choice**: Add `"recruiter_plausibility"` to `_RULES` at level 0, same pattern as `keyword_policy` and `bullet_strategy`.

**Rationale**: Plausibility is a quality/discipline rule, not content-generation. It applies at all creativity levels. The `_RULES` mechanism is proven for injecting consistent prompt text across all builders.

### Decision 2: String defaults for placement fields (not Field(default_factory))

**Choice**: `placement: str = "experience"` and `placement_reason: str = ""`. No `Field()` wrapper needed since strings are immutable.

**Rationale**: Unlike lists/dicts, string defaults don't share mutable state. Simpler than `Field(default="experience")`. Backward compatible: existing callers that don't specify these fields get "experience" placement (current behavior).

### Decision 3: Bolding function in `core/pipeline.py` (not a new file)

**Choice**: Implement `apply_tech_bolding()` in `core/pipeline.py` as a public function, called as a post-generation normalization step.

**Rationale**: The function is tightly coupled to the pipeline flow (called after generation, before validation). A new `core/bolding.py` file adds import complexity for a single ~40-line function. The pipeline module already has similar utilities (`_extract_json`, `_serialize_base_cv`). If it grows significantly, extraction is trivial.

**Alternatives considered**: `core/validation.py` — rejected because bolding is normalization, not validation. It transforms output, it doesn't check it.

### Decision 4: Chain detection via regex, not NLP

**Choice**: Regex pattern for 3+ consecutive capitalized words (potential noun stack). Simple, fast, catches the common case.

**Rationale**: Same rationale as generic-bullet and keyword-stuffing checks — NLP is overkill for soft warnings. A bullet with "Kubernetes container orchestration auto-scaling" has 3 capitalized nouns in a row; the regex catches it. False positives (e.g., "Amazon Web Services EC2" which is a proper name) are acceptable as soft warnings.

### Decision 5: JD mimicry detection via simple similarity heuristic

**Choice**: Check if a bullet's normalized text (lowercased, stopwords removed) shares ≥80% of its bigrams with any JD requirement phrase. Use Python's built-in `difflib.SequenceMatcher` rather than an external NLP library.

**Rationale**: Pure stdlib, no dependencies. The 80% threshold catches near-verbatim copying while allowing natural rewrites. False positives (legitimately similar phrasing) are acceptable as soft warnings.

## Risks / Trade-offs

- **[Risk] Bolding function may produce ugly output for multi-word techs**: "Amazon Web Services" getting bolded mid-sentence could look awkward.
  → **Mitigation**: Multi-word techs are matched as phrases. If the output looks bad, the warning is better than inconsistent bolding. The function can be tuned later.

- **[Risk] Placement validation false positives on legitimately transferred skills**: A candidate might have used a technology in a role but the base CV didn't capture it — placement warning fires incorrectly.
  → **Mitigation**: Warnings are soft. If the evidence map is available (staged pipeline), placement uses that data. In single-shot mode, the check falls back to role technologies comparison, which is less precise but still useful.

- **[Risk] JD mimicry detection false positives**: A well-written bullet may legitimately share phrasing with a JD.
  → **Mitigation**: The bigram similarity threshold of 80% is conservative. A bullet must be very close to the JD wording to trigger. Soft warning only.

- **[Trade-off] Bolding called before validation**: Bolding transforms text before validation sees it. This means validation checks (generic patterns, keyword counts) see bolded text. The `_strip_bold()` helper already handles this for generic checks; keyword counts may need similar treatment if they become sensitive to `**` markers.
