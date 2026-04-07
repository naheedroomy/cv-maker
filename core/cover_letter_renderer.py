"""Cover letter PDF renderer using fpdf2 — pure Python, no system dependencies."""
from __future__ import annotations

from fpdf import FPDF


def _sanitize_text(text: str) -> str:
    """Replace common Unicode characters with latin-1 safe equivalents.

    fpdf2 built-in fonts (Helvetica) only support latin-1.
    Rather than adding a TTF font for rare chars, sanitize first.
    """
    replacements = {
        "\u2013": "-",    # en dash
        "\u2014": "--",   # em dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "-",    # bullet
        "\u00a0": " ",    # non-breaking space
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


def render_cover_letter_pdf(text: str, candidate_name: str = "") -> bytes:
    """Render plain text cover letter to PDF bytes.

    Each newline in the input produces a line break in the PDF.
    Blank lines produce paragraph spacing.

    Args:
        text: The cover letter plain text.
        candidate_name: Unused — kept for API compatibility.

    Returns:
        PDF file content as bytes.
    """
    text = _sanitize_text(text)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.set_left_margin(25)
    pdf.set_right_margin(25)

    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(30, 30, 30)

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            # Blank line — paragraph gap
            pdf.ln(6)
        else:
            pdf.multi_cell(0, 6, stripped)

    return bytes(pdf.output())
