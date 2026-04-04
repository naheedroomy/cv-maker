# tests/test_renderer.py
# Tests for src/cv_maker/renderer.py
# Covers: escape_latex(), render_latex(), render_pdf() (latexmk-absent branch).
# render_pdf() end-to-end PDF compilation tests live in test_renderer_pdf.py (Phase 02-02).
import pytest

from cv_maker.renderer import escape_latex, render_latex, render_pdf


# ---------------------------------------------------------------------------
# escape_latex tests
# ---------------------------------------------------------------------------


class TestEscapeLatex:
    def test_ampersand_escaped(self):
        assert escape_latex("C++ & Python") == r"C++ \& Python"

    def test_percent_escaped(self):
        assert escape_latex("100% remote") == r"100\% remote"

    def test_underscore_escaped(self):
        assert escape_latex("my_module") == r"my\_module"

    def test_backslash_first_no_double_escape(self):
        """A lone backslash must yield \\textbackslash{} — not double-escaped."""
        assert escape_latex("\\") == r"\textbackslash{}"

    def test_all_ten_special_chars(self):
        r"""All 10 LaTeX-reserved characters escaped correctly, backslash first."""
        input_str = r"&%$#_{}~^\\"
        result = escape_latex(input_str)
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
        # Original un-escaped backslash must not appear literally in output
        # (it has been replaced by \textbackslash{})

    def test_no_double_escaping_ampersand(self):
        """Ampersand is replaced once; the backslash in \\& is not then re-escaped."""
        result = escape_latex("&")
        assert result == r"\&"
        # Ensure the backslash itself did not get further escaped
        assert r"\textbackslash{}" not in result

    def test_plain_text_unchanged(self):
        assert escape_latex("Hello World") == "Hello World"

    def test_empty_string(self):
        assert escape_latex("") == ""


# ---------------------------------------------------------------------------
# render_latex tests
# ---------------------------------------------------------------------------


class TestRenderLatex:
    def test_returns_begin_document(self, minimal_tailored_cv):
        latex = render_latex(minimal_tailored_cv)
        assert r"\begin{document}" in latex

    def test_contains_contact_name(self, minimal_tailored_cv):
        latex = render_latex(minimal_tailored_cv)
        assert "Test User" in latex

    def test_no_bare_ampersand_with_special_chars(self, tailored_cv_with_special_chars):
        """No unescaped & should appear in rendered output."""
        import re

        latex = render_latex(tailored_cv_with_special_chars)
        # A bare & not preceded by backslash
        assert not re.search(r"(?<!\\)&", latex), "unescaped ampersand in rendered LaTeX"

    def test_returns_string(self, minimal_tailored_cv):
        assert isinstance(render_latex(minimal_tailored_cv), str)


# ---------------------------------------------------------------------------
# render_pdf — latexmk-absent branch
# ---------------------------------------------------------------------------


class TestRenderPdfLatexmkAbsent:
    def test_raises_file_not_found_when_latexmk_missing(self, monkeypatch):
        """render_pdf raises FileNotFoundError with install hint when latexmk is absent."""
        import shutil

        # Force shutil.which to return None and patch the fallback path
        monkeypatch.setattr(shutil, "which", lambda _: None)
        from pathlib import Path

        monkeypatch.setattr(Path, "exists", lambda self: False)

        with pytest.raises(FileNotFoundError, match="brew install --cask mactex-no-gui"):
            render_pdf("\\documentclass{article}\\begin{document}hello\\end{document}")
