"""Tests for cv_maker.renderer — escape, template rendering, and PDF compilation."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from core.models import TailoredCV
from core.renderer import escape_latex, render_latex, render_pdf

LATEXMK_AVAILABLE = bool(
    shutil.which("latexmk") or Path("/Library/TeX/texbin/latexmk").exists()
)

# ---------------------------------------------------------------------------
# escape_latex — no LaTeX toolchain required
# ---------------------------------------------------------------------------


def test_escape_ampersand() -> None:
    assert escape_latex("C++ & Python") == r"C++ \& Python"


def test_escape_percent() -> None:
    assert escape_latex("100% remote") == r"100\% remote"


def test_escape_underscore() -> None:
    assert escape_latex("my_module") == r"my\_module"


def test_escape_dollar() -> None:
    assert escape_latex("$1000 budget") == r"\$1000 budget"


def test_escape_hash() -> None:
    assert escape_latex("#hashtag") == r"\#hashtag"


def test_escape_braces() -> None:
    assert escape_latex("{braces}") == r"\{braces\}"


def test_escape_tilde() -> None:
    assert escape_latex("tilde~here") == r"tilde\textasciitilde{}here"


def test_escape_caret() -> None:
    assert escape_latex("caret^here") == r"caret\^{}here"


def test_escape_backslash_only() -> None:
    assert escape_latex("\\") == r"\textbackslash{}"


def test_escape_all_ten_chars_no_double_escape() -> None:
    """Regression: all 10 chars escape without double-escaping backslash sequences."""
    raw = r"& % $ # _ { } ~ ^ \\"
    result = escape_latex(raw)
    # Each special char should appear only in its escaped form
    assert r"\&" in result
    assert r"\%" in result
    assert r"\$" in result
    assert r"\#" in result
    assert r"\_" in result
    assert r"\{" in result
    assert r"\}" in result
    assert r"\textasciitilde{}" in result
    assert r"\^{}" in result
    assert r"\textbackslash{}" in result
    # The inserted escape sequences must not be double-escaped
    assert "textbackslash{}textbackslash" not in result


def test_escape_no_special_chars_unchanged() -> None:
    plain = "Python developer with 5 years experience"
    assert escape_latex(plain) == plain


def test_escape_empty_string() -> None:
    assert escape_latex("") == ""


def test_escape_no_double_escaping_ampersand() -> None:
    """Ampersand is replaced once; the backslash in \\& is not then re-escaped."""
    result = escape_latex("&")
    assert result == r"\&"
    assert r"\textbackslash{}" not in result


# ---------------------------------------------------------------------------
# render_latex — no LaTeX toolchain required
# ---------------------------------------------------------------------------


def test_render_latex_returns_string(minimal_tailored_cv: TailoredCV) -> None:
    latex = render_latex(minimal_tailored_cv)
    assert isinstance(latex, str)


def test_render_latex_contains_document_environment(
    minimal_tailored_cv: TailoredCV,
) -> None:
    latex = render_latex(minimal_tailored_cv)
    assert r"\begin{document}" in latex


def test_render_latex_contains_contact_name(
    minimal_tailored_cv: TailoredCV,
) -> None:
    latex = render_latex(minimal_tailored_cv)
    assert "Test User" in latex


def test_render_latex_no_bare_ampersand(
    tailored_cv_with_special_chars: TailoredCV,
) -> None:
    latex = render_latex(tailored_cv_with_special_chars)
    assert not re.search(r"(?<!\\)&", latex), "Unescaped & found in rendered LaTeX"


def test_render_latex_no_bare_percent(
    tailored_cv_with_special_chars: TailoredCV,
) -> None:
    latex = render_latex(tailored_cv_with_special_chars)
    lines = latex.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("%"):
            continue
        assert not re.search(r"(?<!\\)%(?!%)", stripped), (
            f"Unescaped % found in content line: {line!r}"
        )


# ---------------------------------------------------------------------------
# render_latex — Core Competencies pills
# ---------------------------------------------------------------------------


def test_render_latex_core_competencies_present(tailored_cv_with_competencies: TailoredCV) -> None:
    """Core Competencies section appears when core_competencies is populated."""
    latex = render_latex(tailored_cv_with_competencies)
    assert r"\section{Core Competencies}" in latex
    assert r"\pill{Cloud Infrastructure}" in latex


def test_render_latex_core_competencies_absent_when_empty(minimal_tailored_cv: TailoredCV) -> None:
    """Core Competencies section is omitted when core_competencies is empty."""
    latex = render_latex(minimal_tailored_cv)
    assert r"\section{Core Competencies}" not in latex


def test_render_latex_core_competencies_escapes_ampersand(tailored_cv_with_competencies: TailoredCV) -> None:
    """Ampersand in competency phrase is LaTeX-escaped inside pill."""
    latex = render_latex(tailored_cv_with_competencies)
    assert r"\pill{Python \& FastAPI}" in latex


# ---------------------------------------------------------------------------
# render_pdf — latexmk-absent branch (always runs)
# ---------------------------------------------------------------------------


def test_render_pdf_raises_file_not_found_when_latexmk_missing(monkeypatch) -> None:
    """render_pdf raises FileNotFoundError with install hint when latexmk is absent."""
    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setattr(Path, "exists", lambda self: False)
    with pytest.raises(FileNotFoundError, match="brew install --cask mactex-no-gui"):
        render_pdf(r"\documentclass{article}\begin{document}hello\end{document}")


# ---------------------------------------------------------------------------
# render_pdf — requires latexmk (skipped if absent)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not LATEXMK_AVAILABLE, reason="latexmk not installed")
def test_render_pdf_returns_bytes(minimal_tailored_cv: TailoredCV) -> None:
    latex = render_latex(minimal_tailored_cv)
    pdf = render_pdf(latex)
    assert isinstance(pdf, bytes)


@pytest.mark.skipif(not LATEXMK_AVAILABLE, reason="latexmk not installed")
def test_render_pdf_magic_bytes(minimal_tailored_cv: TailoredCV) -> None:
    """PDF files start with %PDF — verify the bytes are a real PDF."""
    latex = render_latex(minimal_tailored_cv)
    pdf = render_pdf(latex)
    assert pdf[:4] == b"%PDF", f"Expected PDF magic bytes, got: {pdf[:8]!r}"


@pytest.mark.skipif(not LATEXMK_AVAILABLE, reason="latexmk not installed")
def test_render_pdf_raises_on_invalid_latex() -> None:
    broken = r"\documentclass{article}\begin{document}\invalid{{broken\end{document}"
    with pytest.raises(RuntimeError, match="LaTeX compilation failed"):
        render_pdf(broken)


@pytest.mark.skipif(not LATEXMK_AVAILABLE, reason="latexmk not installed")
def test_render_pdf_special_chars_cv_compiles(
    tailored_cv_with_special_chars: TailoredCV,
) -> None:
    """CV with special chars (%, &, $) must compile without error after escaping."""
    latex = render_latex(tailored_cv_with_special_chars)
    pdf = render_pdf(latex)
    assert pdf[:4] == b"%PDF"


@pytest.mark.skipif(not LATEXMK_AVAILABLE, reason="latexmk not installed")
def test_render_pdf_with_competencies_compiles(
    tailored_cv_with_competencies: TailoredCV,
) -> None:
    """CV with Core Competencies pills compiles to valid PDF."""
    latex = render_latex(tailored_cv_with_competencies)
    pdf = render_pdf(latex)
    assert pdf[:4] == b"%PDF"
