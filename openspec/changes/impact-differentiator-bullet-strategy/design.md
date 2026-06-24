## Context

The `natural-keyword-evidence-pipeline` change added keyword embedding policy, multi-stage pipeline functions, and keyword-stuffing validation. The intermediate models (`EvidenceMatch`, `EvidenceMap`, etc.) are stable and tested. The prompt-building infrastructure (`_RULES` dict, `_resolve_rule()` for creativity-level thresholds) is well-proven.

This change adds a recruiter-informed bullet-writing strategy on top of that foundation. The core insight is that generic DevOps/cloud bullets ("managed CI/CD pipelines," "deployed Kubernetes clusters") are ubiquitous and fail to differentiate candidates. The fix is prompt-level guidance toward impact-driven bullets (What + How + Result), depth signals, modern practice surfacing, ownership signals, and role-weighted distribution — combined with deterministic validation that flags low-substance bullets.

Constraints (unchanged from prior change):
- No contact/date/company/education/cert/language changes
- Role structure preserved
- No event-loop blocking
- Provider lazy imports
- Per-user API keys
- No UI scope

## Goals / Non-Goals

**Goals:**
1. Add `"bullet_strategy"` prompt rule in `_RULES` at level 0, covering What + How + Result, depth signals, modern practices, ownership signals, role-weighted distribution, ideal composition, and generic-bullet avoidance.
2. Inject the rule into `_build_prompt()`, `_build_system_prompt_for_chat()`, and `generate_tailored_cv()` (Stage 3).
3. Add deterministic generic-bullet validation in `core/validation.py` as soft warnings: task-only detection, generic-phrase blacklist, ownership-signal density check, common-generic-pattern matching.
4. Add `differentiator_categories` and `impact_signals` optional fields to `EvidenceMatch` with `Field(default_factory=list)`.
5. Extend Stage 2 `map_evidence()` prompt to request these fields.
6. Add tests for prompt content, validation behavior, model defaults, and Stage 2 prompt extension.

**Non-Goals:**
- No UI, frontend, backend route, database, Docker, or CI/CD changes.
- No new external dependencies.
- No fabricated metrics or claims.
- No breaking changes to existing models or provider interface.
- No changes to creativity-level gating of the strategy — it applies at all levels (level 0), same as keyword policy.

## Decisions

### Decision 1: Bullet strategy as a `_RULES` entry at level 0

**Choice**: Add `"bullet_strategy"` to `_RULES` at level 0, applying at all creativity levels.

**Rationale**: Same as the keyword policy — it is a formatting/discipline rule, not a content-generation rule. Even at STRICT (level 0), bullets should be well-structured. The `_RULES` mechanism already works for 16+ concerns and ensures consistent propagation to all prompt builders.

**Alternatives considered**: Hard-coding in each prompt builder — rejected for consistency and maintainability, same reason as keyword policy.

### Decision 2: New optional fields on EvidenceMatch (not a new model)

**Choice**: Add `differentiator_categories: list[str]` and `impact_signals: list[str]` directly to `EvidenceMatch` rather than creating a new wrapper model.

**Rationale**: These fields are tightly coupled to evidence mapping — each piece of evidence either supports a differentiator or it doesn't. Adding to `EvidenceMatch` keeps the data co-located and avoids introducing a separate parallel structure. The fields default to empty lists, so existing callers are unaffected.

**Alternatives considered**: A separate `DifferentiatorAnalysis` model — adds complexity with no clear benefit since differentiators are per-evidence-match, not per-CV.

### Decision 3: Deterministic validation without NLP

**Choice**: Regex-based generic-phrase detection, task-only heuristics (bullet length < threshold + no numeric qualifier + no result keyword), and ownership-signal keyword density counting. No ML/NLP.

**Rationale**: Same as keyword-stuffing validation — NLP dependencies are disproportionate for soft warnings. The heuristics catch 80%+ of low-substance bullets. False positives are acceptable since warnings don't block generation.

**Alternatives considered**: LLM-based bullet quality assessment — would require an additional model call, doubling cost and latency. Rejected.

### Decision 4: Generic pattern matching via regex, not fuzzy similarity

**Choice**: Maintain a set of regex patterns for common generic bullets (e.g., `r"\b(managed|deployed|configured|set up|used)\s+\w+\s+(for|with|to|in|on)\b"`) rather than implementing character-similarity matching.

**Rationale**: Regex is deterministic, fast, and sufficient for the known generic patterns. Character similarity (80% match threshold) would require a diff algorithm and tuning for false positives — overengineered for soft warnings. If a bullet is genuinely generic, regex catches its structural pattern; if it's specific enough to evade regex, it's probably not a problem.

### Decision 5: Ownership signal density check as percentage threshold

**Choice**: Count bullets containing ownership/impact keywords and warn if < 20% of total bullets have a signal. This is a single aggregate check, not per-bullet.

**Rationale**: Per-bullet ownership checking would produce too many false positives (not every bullet needs ownership language). An aggregate density check flags the CV-level pattern of low-ownership writing while tolerating individual non-ownership bullets.

## Risks / Trade-offs

- **[Risk] Prompt size inflation**: The existing prompt is ~2000 words. The bullet strategy rule adds 15-25 lines (~200-300 words). 
  → **Mitigation**: Keep the strategy rule concise and directive, not verbose. Use bullet-point format. The prompt already has similar-sized sections (substitution rule, inference rules).

- **[Risk] Over-constraining bullet writing quality**: Stricter guidelines might produce formulaic bullets.
  → **Mitigation**: The strategy is aspirational, not enforced. Validation emits soft warnings, not hard failures. The prompt emphasizes natural language and avoiding template-like repetition.

- **[Risk] Generic-bullet validation false positives on valid bullets**: A concise bullet with an action verb + tool might be perfectly good but flagged as "task-only."
  → **Mitigation**: The task-only heuristic checks multiple signals (length, presence of numeric qualifier, presence of result keyword, presence of context phrase). A bullet that's short but contains a result or scale indicator passes. Bullets flagged as task-only get a warning, not removal.

- **[Risk] Stage 2 prompt extension may confuse models**: Adding `differentiator_categories` and `impact_signals` to the JSON schema adds complexity.
  → **Mitigation**: Both fields default to empty lists. If the model ignores them, the pipeline still works — the fields simply stay empty. The prompt explicitly says to leave them empty when no differentiator applies.

- **[Trade-off] No backward incompatibility**: All new fields use `Field(default_factory=list)`. No existing test code or caller needs modification. The bullet strategy prompt rule may subtly shift LLM output quality, but golden-file tests with mock providers isolate this.
