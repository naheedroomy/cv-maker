"""Post-generation validation — compare BaseCV vs TailoredCV for hard violations.

Runs after every TailoredCV.model_validate() in pipeline/provider paths.
Hard violations raise ValueError. Soft issues append warning strings.
"""
from __future__ import annotations

import logging
import re

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


def validate_tailored_cv(base: BaseCV, tailored: TailoredCV) -> list[str]:
    """Compare BaseCV vs TailoredCV.

    Raises ValueError on hard violations (contact changed, role count
    mismatch, company/title/date change). Returns soft warnings for
    review (suspicious new metrics, etc.).

    The caller should log warnings and optionally surface them to the user.
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
    """
    base_by_company = {e.company.strip().lower(): e.title.strip() for e in base.experience}
    for te in tailored.experience:
        key = te.company.strip().lower()
        if key not in base_by_company:
            continue  # already caught by _check_companies
        original = base_by_company[key]
        if te.title.strip() != original:
            warnings.append(
                f"Title corrected for '{te.company}': "
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
