"""Post-generation validation — compare BaseCV vs TailoredCV for hard violations.

Runs after every TailoredCV.model_validate() in pipeline/provider paths.
Hard violations raise ValueError. Soft issues append warning strings.
"""
from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher

from core.models import BaseCV, TailoredCV

logger = logging.getLogger(__name__)


def check_tailored_cv(base: BaseCV, tailored: TailoredCV) -> None:
    """Validate and log warnings. Raises ValueError on hard violations.

    Thin wrapper around validate_tailored_cv — call this from any provider
    path after TailoredCV.model_validate() succeeds.
    """
    warnings = validate_tailored_cv(base, tailored)
    for w in warnings:
        logger.warning("TailoredCV soft warning: %s", w)

# Regex that looks for invented numeric metrics injected by an LLM.
# Catches patterns like "40+ instances", "99.95% uptime", "12-member team",
# "managed $2M budget", "3 regions". This is intentionally broad — it only
# checks for new numbers that weren't in the base CV. Known legitimate numbers
# (dates, version numbers already in base) are not flagged.
_METRIC_RE = re.compile(
    r"\b\d+[+\-]?\s*(?:\S+\s+)?(?:%|percent|K|M|B|users?|RPS|instances?|members?|regions?|"
    r"services?|environments?|hours?|days?|weeks?|months?|years?|"
    r"deploy|pipeline|cluster|team|node)\b",
    re.IGNORECASE,
)
# Dollar amounts like "$2M", "$500K", "$2 million"
_DOLLAR_RE = re.compile(r"\$\d+(?:\.\d+)?[KMB]?(?:\s*(?:million|billion|thousand))?")
# Uptime patterns like "99.9%", "99.95%"
_UPTIME_RE = re.compile(r"\b\d{2,3}\.\d+%?\s*uptime\b", re.IGNORECASE)

# Keyword alias map — maps known tech abbreviations to canonical forms for
# comparison during keyword-stuffing checks.
_KEYWORD_ALIASES: dict[str, str] = {
    "k8s": "kubernetes",
    "gh actions": "github actions",
    "gha": "github actions",
    "ec2": "aws ec2",
    "ecs": "aws ecs",
    "eks": "aws eks",
    "rds": "aws rds",
    "s3": "aws s3",
    "gke": "google kubernetes engine",
    "gcb": "google cloud build",
    "tf": "terraform",
    "cicd": "ci/cd",
    "iac": "infrastructure as code",
    "oop": "object-oriented programming",
    "fp": "functional programming",
}

# Suffix patterns to strip for keyword stemming (non-destructive — used only
# for comparison, not for display).
_KEYWORD_SUFFIX_RE = re.compile(r"(ing|ed|s|ment|tion|ing|ness|able|ible)$", re.IGNORECASE)

# List of weak action verbs that suggest a bullet has action language
# (vs. being a bare keyword list).
_ACTION_VERBS = frozenset({
    "built", "designed", "implemented", "developed", "created", "led", "managed",
    "deployed", "migrated", "optimized", "reduced", "increased", "automated",
    "configured", "integrated", "launched", "architected", "engineered",
    "maintained", "monitored", "scaled", "secured", "tested", "delivered",
    "owned", "drove", "established", "improved", "streamlined", "orchestrated",
})

# Generic phrases that suggest passive participation rather than active ownership.
# Matched case-insensitively with word boundaries.
_GENERIC_PHRASE_RE = re.compile(
    r"\b(?:worked on|responsible for|helped with|involved in|collaborated with|"
    r"assisted with|participated in|supported\b(?!\s+(?:decision|resolution|team|"
    r"initiative|migration|launch|deployment))|handled\b|was part of)\b",
    re.IGNORECASE,
)

# Keywords that indicate ownership, impact, or leadership in a bullet.
# Used for aggregate density checking.
_OWNERSHIP_IMPACT_KEYWORDS = frozenset({
    "incident", "on-call", "rca", "reduced", "improved", "automated",
    "mentored", "owned", "led", "designed", "architected", "saved",
    "optimized", "standardized", "streamlined", "eliminated", "enabled",
    "launched", "migrated", "scaled", "achieved", "delivered",
    "root cause", "postmortem", "sla", "slo", "sli",
    "uptime", "availability", "reliability",
})

# Regex for common generic DevOps/cloud bullets that appear on most resumes.
# These patterns catch task+tool phrasing without specificity, context, or result.
_GENERIC_PATTERN_RE = re.compile(
    r"^(?:managed|deployed|configured|used|set up|setup|provisioned)\s+"
    r"(?:a |an |the )?\w+(?:\s+\w+){0,2}\s+(?:for|with|to|in|on|using|across)\b",
    re.IGNORECASE,
)


def validate_tailored_cv(
    base: BaseCV, tailored: TailoredCV, jd_keywords: list[str] | None = None, jd_text: str = ""
) -> list[str]:
    """Compare BaseCV vs TailoredCV.

    Raises ValueError on hard violations (contact changed, role count
    mismatch, company/title/date change). Returns soft warnings for
    review (suspicious new metrics, keyword stuffing, etc.).

    The caller should log warnings and optionally surface them to the user.

    Args:
        base: The original base CV.
        tailored: The AI-tailored CV to validate.
        jd_keywords: Optional list of JD keyword phrases. When provided,
            keyword-stuffing soft checks run. When None (default, for
            backward compat), keyword checks are skipped entirely.
    """
    warnings: list[str] = []

    # ── Hard checks ──────────────────────────────────────────────────
    _check_contact(base, tailored)
    _check_experience_count(base, tailored)
    _check_companies(base, tailored)
    _check_titles(base, tailored, warnings)  # soft: corrects + warns
    _check_dates(base, tailored)
    _check_education(base, tailored)
    _check_certifications(base, tailored)
    _check_languages(base, tailored)

    # ── Soft checks (invented metrics) ───────────────────────────────
    _check_invented_metrics(base, tailored, warnings)

    # ── Soft checks (keyword stuffing) ───────────────────────────────
    if jd_keywords:
        _check_keyword_stuffing(base, tailored, jd_keywords, warnings)

    # ── Soft checks (generic / low-substance bullets) ─────────────────
    _check_generic_bullets(base, tailored, warnings)

    # ── Soft checks (keyword placement / plausibility) ────────────────
    _check_keyword_placement(base, tailored, warnings)
    _check_awkward_chains(tailored, warnings)
    if jd_text:
        _check_jd_mimicry(tailored, jd_text, warnings)
    _check_highlighted_tech_references(tailored, warnings)
    _check_role_tech_consistency(tailored, warnings)
    _check_core_competencies_tool_leakage(tailored, warnings)

    return warnings


# ── Hard-check helpers ────────────────────────────────────────────────────


def _check_contact(base: BaseCV, tailored: TailoredCV) -> None:
    bc, tc = base.contact, tailored.contact
    fields = ["name", "email", "linkedin", "github", "phone", "location", "work_authorization"]
    for f in fields:
        bv = getattr(bc, f, None)
        tv = getattr(tc, f, None)
        if _normalise(bv) != _normalise(tv):
            raise ValueError(
                f"Contact field '{f}' changed from {bv!r} to {tv!r}. "
                f"Contact info must not be modified by AI."
            )


def _check_experience_count(base: BaseCV, tailored: TailoredCV) -> None:
    if len(base.experience) != len(tailored.experience):
        raise ValueError(
            f"Experience role count changed: {len(base.experience)} in base CV, "
            f"{len(tailored.experience)} in tailored CV. Roles must not be added or removed."
        )


def _check_companies(base: BaseCV, tailored: TailoredCV) -> None:
    base_companies = {e.company.strip().lower() for e in base.experience}
    tailored_companies = {e.company.strip().lower() for e in tailored.experience}
    if base_companies != tailored_companies:
        missing = base_companies - tailored_companies
        added = tailored_companies - base_companies
        msg_parts = []
        if missing:
            msg_parts.append(f"removed: {missing}")
        if added:
            msg_parts.append(f"added: {added}")
        raise ValueError(
            f"Company names changed — {'; '.join(msg_parts)}. "
            f"Companies must not be modified by AI."
        )


def _check_titles(base: BaseCV, tailored: TailoredCV, warnings: list[str]) -> None:
    """Correct job title drift back to the base CV title (soft, not hard failure).

    Title retitling is a common LLM behaviour that rarely changes substance.
    Instead of failing the generation, we silently reset the title and warn.

    Matches roles by (company, start, end) so that duplicate roles at the same
    company with different titles and date ranges are each corrected to their
    own base title, not a single overwritten title.
    """
    base_by_role = {
        (e.company.strip().lower(), e.start, e.end): e.title.strip()
        for e in base.experience
    }
    for te in tailored.experience:
        key = (te.company.strip().lower(), te.start, te.end)
        if key not in base_by_role:
            continue  # already caught by _check_companies / _check_dates
        original = base_by_role[key]
        if te.title.strip() != original:
            warnings.append(
                f"Title corrected for '{te.company}' ({te.start}–{te.end}): "
                f"'{te.title.strip()}' -> '{original}'"
            )
            te.title = original


def _check_dates(base: BaseCV, tailored: TailoredCV) -> None:
    base_dates = {(e.company.strip().lower(), e.start, e.end) for e in base.experience}
    for te in tailored.experience:
        key = (te.company.strip().lower(), te.start, te.end)
        if key not in base_dates:
            # Find the matching company to report the diff
            base_entry = next(
                (e for e in base.experience if e.company.strip().lower() == te.company.strip().lower()),
                None,
            )
            if base_entry is None:
                continue  # already caught by _check_companies
            raise ValueError(
                f"Date changed for '{te.company}': "
                f"({base_entry.start}, {base_entry.end}) -> ({te.start}, {te.end}). "
                f"Dates must not be modified by AI."
            )


def _check_education(base: BaseCV, tailored: TailoredCV) -> None:
    if len(base.education) != len(tailored.education):
        raise ValueError(
            f"Education entries count changed: {len(base.education)} -> "
            f"{len(tailored.education)}. Education must not be modified by AI."
        )
    base_insts = {e.institution.strip().lower() for e in base.education}
    tailored_insts = {e.institution.strip().lower() for e in tailored.education}
    if base_insts != tailored_insts:
        raise ValueError(
            f"Education institutions changed: {base_insts} -> {tailored_insts}. "
            f"Education must not be modified by AI."
        )


def _check_certifications(base: BaseCV, tailored: TailoredCV) -> None:
    # Certifications should not be dropped (adding is questionable but softer)
    base_set = {c.strip() for c in base.certifications}
    tailored_set = {c.strip() for c in tailored.certifications}
    dropped = base_set - tailored_set
    if dropped:
        raise ValueError(
            f"Certifications dropped: {dropped}. "
            f"Certifications from base CV must not be removed."
        )


def _check_languages(base: BaseCV, tailored: TailoredCV) -> None:
    base_langs = {(l.language.strip().lower(), l.level.strip().lower()) for l in base.languages}
    tailored_langs = {(l.language.strip().lower(), l.level.strip().lower()) for l in tailored.languages}
    if base_langs != tailored_langs:
        raise ValueError(
            f"Languages changed: {base_langs} -> {tailored_langs}. "
            f"Languages must be pass-through from base CV."
        )


# ── Soft checks ───────────────────────────────────────────────────────────


def _check_invented_metrics(base: BaseCV, tailored: TailoredCV, warnings: list[str]) -> None:
    """Check for numeric metrics/claims in tailored that don't appear in base.

    Aggregates all bullet text from both CVs and flags numbers that appear
    only in the tailored output. This is intentionally looser than it could be —
    a verbatim REST API count of "10M" is fine if it was in the base CV.
    """
    base_text = _all_bullet_text(base)
    tailored_text = _all_bullet_text(tailored)

    base_numbers = set()
    for m in _METRIC_RE.finditer(base_text):
        base_numbers.add(m.group().strip().lower())
    for m in _DOLLAR_RE.finditer(base_text):
        base_numbers.add(m.group().strip().lower())
    for m in _UPTIME_RE.finditer(base_text):
        base_numbers.add(m.group().strip().lower())

    for m in _METRIC_RE.finditer(tailored_text):
        val = m.group().strip().lower()
        if val not in base_numbers:
            warnings.append(f"Possible invented metric in tailored CV: '{m.group()}'")

    for m in _DOLLAR_RE.finditer(tailored_text):
        val = m.group().strip().lower()
        if val not in base_numbers:
            warnings.append(f"Possible invented dollar amount in tailored CV: '{m.group()}'")

    for m in _UPTIME_RE.finditer(tailored_text):
        val = m.group().strip().lower()
        if val not in base_numbers:
            warnings.append(f"Possible invented uptime claim in tailored CV: '{m.group()}'")


def _all_bullet_text(cv: BaseCV | TailoredCV) -> str:
    return " ".join(b for e in cv.experience for b in e.bullets)


def _normalise(v: object) -> str:
    """Normalise a field value for comparison — treat None, '', and whitespace-only as equal."""
    if v is None:
        return ""
    return str(v).strip()


# ── Keyword-stuffing soft checks ────────────────────────────────────────────


def _normalize_keyword(kw: str) -> str:
    """Normalize a keyword for comparison: lowercase, strip punctuation,
    resolve known aliases, and apply simple suffix stemming.
    """
    kw = kw.strip().lower()
    # Strip leading/trailing punctuation
    kw = kw.strip(".,;:!?()[]{}'\"*")
    # Resolve aliases
    kw = _KEYWORD_ALIASES.get(kw, kw)
    # Simple suffix stemming (non-destructive — only for comparison)
    kw = _KEYWORD_SUFFIX_RE.sub("", kw)
    return kw


def _count_jd_keywords_in_text(text: str, jd_keywords: set[str]) -> int:
    """Count how many distinct JD keywords appear in the given text.
    Uses normalized matching (case-insensitive, aliased, stemmed).
    """
    text_lower = text.lower()
    found: set[str] = set()
    for kw in jd_keywords:
        norm = _normalize_keyword(kw)
        if norm and norm in text_lower:
            found.add(norm)
    return len(found)


def _has_action_verb(text: str) -> bool:
    """Check if text contains at least one action verb suggesting
    substantive content rather than a bare keyword list.
    """
    words = text.lower().split()
    return any(w in _ACTION_VERBS for w in words)


def _check_keyword_stuffing(
    base: BaseCV, tailored: TailoredCV, jd_keywords: list[str], warnings: list[str]
) -> None:
    """Soft-check for keyword stuffing in the tailored CV.

    Checks:
    - Excessive keyword density per bullet (3+ distinct JD keywords)
    - Bare keyword-list bullets (comma-separated tech without action verbs)
    - Keyword overuse across many bullets (4+ bullets for same keyword)
    - Unsubstantiated keywords in skills section

    All findings are appended as soft warnings — never hard failures.
    """
    norm_keywords: set[str] = {_normalize_keyword(k) for k in jd_keywords}
    norm_keywords.discard("")  # remove empty strings from normalization

    # Collect base CV evidence: all tech names, skills, and bullet text
    base_techs: set[str] = set()
    for e in base.experience:
        for t in e.technologies:
            base_techs.add(t.strip().lower())
    base_skills_lower = {s.strip().lower() for s in base.skills}
    base_techs |= base_skills_lower

    # ── Per-bullet checks ────────────────────────────────────────────
    all_bullets: list[str] = []
    for exp in tailored.experience:
        for bi, bullet in enumerate(exp.bullets):
            all_bullets.append(bullet)
            count = _count_jd_keywords_in_text(bullet, norm_keywords)
            if count >= 3:
                warnings.append(
                    f"Keyword stuffing suspected: bullet contains {count} "
                    f"distinct JD keywords — '{bullet[:80]}...'"
                )
            # Bare keyword list detection: if bullet has no action verb
            # and reads like a tech enumeration
            if not _has_action_verb(bullet) and count >= 2:
                # Heuristic: if the bullet is short and has multiple commas,
                # it's likely a bare list
                comma_count = bullet.count(",")
                if comma_count >= 2 and len(bullet.split()) < 20:
                    warnings.append(
                        f"Keyword list detected: bullet appears to be a bare "
                        f"technology enumeration without substantive action — "
                        f"'{bullet[:80]}...'"
                    )

    # ── Keyword reuse across bullets ─────────────────────────────────
    keyword_bullet_counts: dict[str, int] = {}
    for kw in norm_keywords:
        for bullet in all_bullets:
            if _normalize_keyword(kw) in bullet.lower():
                keyword_bullet_counts[kw] = keyword_bullet_counts.get(kw, 0) + 1

    for kw, count in keyword_bullet_counts.items():
        if count >= 4:
            warnings.append(
                f"Keyword overused: '{kw}' appears in {count} bullets — "
                f"natural distribution is typically 1-3 mentions"
            )

    # ── Skills section keyword dumping ───────────────────────────────
    individual_skills: list[str] = []
    for s in tailored.skills:
        if ":" in s:
            _, rest = s.split(":", 1)
            individual_skills.extend(item.strip() for item in rest.split(",") if item.strip())
        elif s.strip():
            individual_skills.append(s.strip())

    for skill in individual_skills:
        skill_norm = skill.strip().lower()
        # Check if this skill appears to be a JD keyword with no base CV evidence
        is_jd_keyword = any(
            _normalize_keyword(k) in skill_norm or skill_norm in _normalize_keyword(k)
            for k in jd_keywords
        )
        if is_jd_keyword and skill_norm not in base_techs:
            # Also check if it appears in any tailored bullet (weak evidence)
            in_bullets = any(skill_norm in b.lower() for b in all_bullets)
            if not in_bullets:
                warnings.append(
                    f"Unsubstantiated keyword in skills: '{skill}' has no "
                    f"evidence trace in base CV"
                )


# ── Generic / low-substance bullet soft checks ────────────────────────────────


def _check_generic_bullets(
    base: BaseCV, tailored: TailoredCV, warnings: list[str]
) -> None:
    """Soft-check for generic, low-substance bullets.

    Checks:
    - Generic phrasing (worked on, responsible for, etc.)
    - Common generic DevOps bullet patterns (task+tool without specificity)
    - Task-only bullets lacking specificity, context, or result
    - Low ownership/impact signal density across all bullets

    All findings are soft warnings — never hard failures.
    """
    all_bullets: list[str] = [b for e in tailored.experience for b in e.bullets]
    if not all_bullets:
        return

    # Strip **bold** markdown for pattern-based checks so that
    # "Managed **Kubernetes** deployments" matches the same patterns
    # as "Managed Kubernetes deployments".
    def _strip_bold(text: str) -> str:
        return text.replace("**", "")

    # ── Per-bullet: generic phrase detection ──────────────────────────
    for bullet in all_bullets:
        m = _GENERIC_PHRASE_RE.search(bullet)
        if m:
            warnings.append(
                f"Generic phrase detected: '{m.group()}' suggests passive "
                f"participation — use active ownership language — "
                f"'{bullet[:80]}...'"
            )

    # ── Per-bullet: common generic DevOps pattern detection ───────────
    for bullet in all_bullets:
        stripped = _strip_bold(bullet)
        if _GENERIC_PATTERN_RE.match(stripped.strip()):
            words = stripped.split()
            has_number = bool(re.search(r"\d+", stripped))
            has_result = any(kw in stripped.lower() for kw in [
                "reduce", "improve", "increase", "decrease", "save", "cut",
                "achieve", "deliver", "enable", "launch", "migrate", "scale",
                "standardize", "automate", "optimize", "%", "percent",
            ])
            # Only flag if the bullet is short AND has no numeric/result signal.
            # Longer bullets with the same starting pattern often add context.
            if len(words) <= 12 and not has_number and not has_result:
                warnings.append(
                    f"Common generic pattern detected: '{bullet[:80]}...' — "
                    f"add specificity, scale, and result"
                )

    # ── Per-bullet: task-only detection ───────────────────────────────
    # A bullet is task-only if it's very short, has no numeric qualifier,
    # no result/context language, and no specific technology/tool mention
    # beyond the action verb.
    for bullet in all_bullets:
        stripped = _strip_bold(bullet)
        words = stripped.split()
        has_number = bool(re.search(r"\d+", stripped))
        has_result = any(kw in stripped.lower() for kw in [
            "reduce", "improve", "increase", "decrease", "save", "cut",
            "achieve", "deliver", "enable", "launch", "migrate", "scale",
            "standardize", "automate", "optimize", "%", "percent",
            "uptime", "availability", "team", "across", "adopted by",
            "resulting in", "leading to",
        ])
        # Also consider specific nouns/technologies as evidence of substance
        has_specific_noun = bool(re.search(
            r"\b(?:api|service|platform|system|module|library|framework|"
            r"pipeline|cluster|infrastructure|tool|internal|custom|"
            r"microservice|database|network|application)s?\b",
            bullet, re.IGNORECASE,
        ))
        if len(words) <= 6 and not has_number and not has_result and not has_specific_noun:
            warnings.append(
                f"Generic bullet detected: task-only without specificity, "
                f"context, or result — '{bullet[:80]}...'"
            )

    # ── Aggregate: ownership / impact signal density ──────────────────
    # Only meaningful when there are enough bullets to assess a pattern.
    if len(all_bullets) >= 5:
        ownership_count = 0
        for bullet in all_bullets:
            bullet_lower = bullet.lower()
            if any(kw in bullet_lower for kw in _OWNERSHIP_IMPACT_KEYWORDS):
                ownership_count += 1
        density = ownership_count / len(all_bullets)
        if density < 0.20:
            pct = int(density * 100)
            warnings.append(
                f"Low ownership signal: only {pct}% of bullets contain "
                f"impact/ownership language — consider surfacing results, "
                f"mentorship, or ownership where base CV supports it"
            )


# ── Keyword placement / plausibility soft checks ─────────────────────────────


def _check_keyword_placement(
    base: BaseCV, tailored: TailoredCV, warnings: list[str]
) -> None:
    """Warn when a tailored role technology has no evidence in that role's base CV."""
    # Build per-role evidence from base CV, keyed by (company, start, end)
    base_role_evidence: dict[tuple[str, str, str], tuple[set[str], str]] = {}
    base_skills_lower = {s.strip().lower() for s in base.skills}
    for e in base.experience:
        key = (e.company.strip().lower(), e.start, e.end or "")
        techs = {t.strip().lower() for t in e.technologies}
        bullets_text = " ".join(b.lower() for b in e.bullets)
        base_role_evidence[key] = (techs, bullets_text)

    for exp in tailored.experience:
        key = (exp.company.strip().lower(), exp.start, exp.end or "")
        evidence = base_role_evidence.get(key)
        if evidence is None:
            continue
        base_techs, base_bullets = evidence
        tailored_techs = {t.strip().lower() for t in exp.technologies}
        for tech in tailored_techs:
            if len(tech) <= 2:
                continue
            tech_lower = tech.lower()
            # Skip if tech is in base role technologies, base role bullets, or base skills
            if tech_lower in base_techs:
                continue
            if tech_lower in base_bullets:
                continue
            if tech_lower in base_skills_lower:
                continue
            warnings.append(
                f"Suspicious placement: '{tech}' may not be grounded in "
                f"'{exp.company}' ({exp.start}–{exp.end}) role's base-CV evidence"
            )


def _check_awkward_chains(tailored: TailoredCV, warnings: list[str]) -> None:
    """Detect 3+ consecutive capitalized nouns/tech terms (awkward keyword chains)."""
    # Common action verbs that are often capitalized at bullet start but not tech terms
    _COMMON_VERBS = frozenset({
        "built", "managed", "designed", "implemented", "developed", "created",
        "led", "deployed", "migrated", "optimized", "reduced", "increased",
        "automated", "configured", "integrated", "launched", "architected",
        "engineered", "maintained", "monitored", "scaled", "secured", "tested",
        "delivered", "owned", "drove", "established", "improved", "streamlined",
        "orchestrated", "achieved",
    })
    _CHAIN_RE = re.compile(
        r"\b([A-Z][a-zA-Z0-9+#.-]*(?:\s+[A-Z][a-zA-Z0-9+#.-]*){2,})\b"
    )
    for exp in tailored.experience:
        for bullet in exp.bullets:
            stripped = bullet.replace("**", "")
            for m in _CHAIN_RE.finditer(stripped):
                words = m.group().split()
                # Filter out common verbs
                tech_words = [w for w in words if w.lower() not in _COMMON_VERBS]
                if len(tech_words) >= 3:
                    warnings.append(
                        f"Awkward term chain detected: {len(tech_words)} "
                        f"consecutive capitalized terms — '{m.group()}' — "
                        f"use natural project language"
                    )
                    break  # one warning per bullet


def _check_jd_mimicry(
    tailored: TailoredCV, jd_text: str, warnings: list[str]
) -> None:
    """Warn when bullet text closely mimics JD phrasing (bigram similarity >= 80%)."""
    # Extract JD requirement-like sentences (lines with 6+ words)
    jd_lines = [l.strip() for l in jd_text.splitlines() if len(l.split()) >= 6]
    if not jd_lines:
        return

    for exp in tailored.experience:
        for bullet in exp.bullets:
            bullet_norm = bullet.replace("**", "").lower()
            for jd_line in jd_lines:
                jd_norm = jd_line.lower()
                # Use SequenceMatcher for quick similarity check
                ratio = SequenceMatcher(None, bullet_norm, jd_norm).ratio()
                if ratio >= 0.80 and len(bullet_norm) > 15:
                    warnings.append(
                        f"Possible JD mimicry: bullet phrasing closely matches "
                        f"job description language ({int(ratio*100)}% similarity) — "
                        f"'{bullet[:80]}...'"
                    )
                    break


def _check_highlighted_tech_references(
    tailored: TailoredCV, warnings: list[str]
) -> None:
    """Warn if a highlighted technology is never referenced in any bullet."""
    all_bullet_text = " ".join(
        b.replace("**", "").lower()
        for e in tailored.experience for b in e.bullets
    )
    for tech in tailored.highlighted_technologies:
        tech_stripped = tech.strip()
        if not tech_stripped:
            continue
        # Word-boundary phrase match (handles +, #, ., / in tech names safely)
        pattern = re.compile(
            r"(?<!\w)" + re.escape(tech_stripped) + r"(?!\w)", re.IGNORECASE,
        )
        if not pattern.search(all_bullet_text):
            warnings.append(
                f"Highlighted technology '{tech}' is never referenced in "
                f"bullets — consider adding or removing"
            )


def _check_role_tech_consistency(
    tailored: TailoredCV, warnings: list[str]
) -> None:
    """Warn if a role's technologies field lists tools not in its bullets or skills."""
    all_skills_lower = {s.strip().lower() for s in tailored.skills}
    for exp in tailored.experience:
        if not exp.bullets:
            continue
        role_bullet_text = " ".join(
            b.replace("**", "").lower() for b in exp.bullets
        )
        for tech in exp.technologies:
            tech_stripped = tech.strip()
            if not tech_stripped:
                continue
            tech_lower = tech_stripped.lower()
            # Word-boundary phrase match in skills
            in_skills = any(
                re.search(r"(?<!\w)" + re.escape(tech_stripped) + r"(?!\w)",
                          s, re.IGNORECASE)
                for s in tailored.skills
            )
            # Word-boundary phrase match in bullets
            in_bullets = bool(
                re.search(r"(?<!\w)" + re.escape(tech_stripped) + r"(?!\w)",
                          role_bullet_text, re.IGNORECASE)
            )
            if in_bullets or in_skills:
                continue
            warnings.append(
                f"Role technology '{tech}' not referenced in any bullet "
                f"for '{exp.company}' role"
            )


def _check_core_competencies_tool_leakage(
    tailored: TailoredCV, warnings: list[str]
) -> None:
    """Warn if core_competencies contains concrete tool names instead of capabilities."""
    # Collect known concrete tools from highlighted_technologies and role techs
    concrete_tools: set[str] = {t.strip().lower() for t in tailored.highlighted_technologies}
    for exp in tailored.experience:
        concrete_tools |= {t.strip().lower() for t in exp.technologies}

    # Tool-like patterns: CamelCase, dot-separated, or common tool names
    for comp in tailored.core_competencies:
        comp_lower = comp.strip().lower()
        if comp_lower in concrete_tools:
            warnings.append(
                f"Concrete tool '{comp}' in core_competencies — use "
                f"highlighted_technologies for tools; core_competencies is "
                f"for capabilities/methodologies (e.g., GitOps, IaC, CI/CD)"
            )
