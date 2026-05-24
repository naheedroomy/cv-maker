"""Lightweight cover-letter audit — regex-based AI-tell scanner and stats.

Runs after cover letter generation. Returns structured warnings the caller
can log, store in revision_notes, or use to trigger a retry.
"""
from __future__ import annotations

import re

# ── AI-tell regexes ────────────────────────────────────────────────────────
# Grouped by category. Each is a (label, pattern, replacement_suggestion) tuple.

_AI_VOCAB = [
    # Overused AI vocabulary words (from Wikipedia Signs of AI Writing)
    ("delve", r"\bdelve[sd]?\b", "investigate / explore"),
    ("tapestry", r"\btapestry\b", "fabric / mix / combination"),
    ("intricacy", r"\bintricac(?:y|ies)\b", "detail / details"),
    ("showcase", r"\bshowcas(?:e[ds]?|ing)\b", "show / present / demonstrate"),
    ("foster", r"\bfoster(?:s|ed|ing)?\b", "encourage / build"),
    ("garner", r"\bgarners?\b", "earn / gain / attract"),
    ("landscape", r"\blandscape\b", "field / area / environment"),
    ("underscore", r"\bunderscor(?:e[ds]?|ing)\b", "highlight / emphasize"),
    ("pivotal", r"\bpivotal\b", "key / central / important"),
    ("testament", r"\btestament\b", "proof / evidence / sign"),
    ("in order to", r"\bin order to\b", "to"),
    ("due to the fact that", r"\bdue to the fact that\b", "because"),
    ("leveraging", r"\bleveraging\b", "using"),
    ("fostering", r"\bfostering\b", "building / encouraging"),
    ("seamless", r"\bseamless\b", "smooth"),
    ("robust", r"\brobust\b", "reliable / solid"),
    # Synonym cycling check — not easily regex-able, skip
]

_STYLE_TELLS = [
    # Em dashes
    ("em_dash", r"[\u2014]", "use period or comma instead"),
    # Not only ... but also
    ("not_only_but_also", r"\bnot only\b.*?\bbut\b", "state the point directly"),
    # Achievement chains: 3+ items in a comma-separated list within one sentence
    # Detected as: 3+ consecutive ", [verb]ing" or ", [verb]ed" patterns
    # Broad but useful signal
    ("participial_padding", r",\s*(?:ensuring|contributing|showcasing|emphasizing|fostering|garnering|reflecting|symbolizing|highlighting|underscoring|leveraging|enabling|allowing)\b", "end the sentence; start a new one"),
]

_GENERIC_CLOSINGS = [
    # Generic closings that signal AI-generated cover letters
    ("I look forward to discussing", r"\bI (?:would welcome the opportunity to |look forward to )(?:discuss|hear|speak)", "replace with specific next step"),
    ("I am excited to apply", r"\bI am (?:excited|thrilled|eager) to (?:apply|submit)", "state why you want this specific role"),
    ("proven track record", r"\bproven track record\b", "specific achievement instead"),
    ("results-driven", r"\bresults[- ]driven\b", "specific result"),
]


def audit_cover_letter(text: str) -> dict:
    """Scan cover letter text for AI tells. Returns a dict with warnings.

    Returns:
        dict with keys:
        - word_count: int
        - paragraph_count: int
        - ai_vocab_hits: list of (word_found, suggestion)
        - style_tells: list of (tell_name, suggestion)
        - generic_closings: list of (closing_found, suggestion)
        - warnings: list of human-readable warning strings
        - is_clean: bool (True if no issues found)
    """
    result: dict = {
        "word_count": len(text.split()),
        "paragraph_count": len([p for p in text.split("\n\n") if p.strip()]) if text else 0,
        "ai_vocab_hits": [],
        "style_tells": [],
        "generic_closings": [],
        "warnings": [],
    }

    # Check AI vocab
    for label, pattern, suggestion in _AI_VOCAB:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            result["ai_vocab_hits"].append((label, suggestion))
            result["warnings"].append(f"AI vocab '{label}' found (try: {suggestion})")

    # Check style tells
    for label, pattern, suggestion in _STYLE_TELLS:
        if re.search(pattern, text, re.IGNORECASE):
            result["style_tells"].append((label, suggestion))
            result["warnings"].append(f"Style tell: {label} ({suggestion})")

    # Check generic closings
    for label, pattern, suggestion in _GENERIC_CLOSINGS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            result["generic_closings"].append((label, suggestion))
            result["warnings"].append(f"Generic closing '{label}' found ({suggestion})")

    result["is_clean"] = (
        not result["ai_vocab_hits"]
        and not result["style_tells"]
        and not result["generic_closings"]
    )

    return result
