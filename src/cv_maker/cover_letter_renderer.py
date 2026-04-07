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

    Args:
        text: The cover letter plain text (paragraphs separated by blank lines).
        candidate_name: Optional name to display as a header.

    Returns:
        PDF file content as bytes.
    """
    text = _sanitize_text(text)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.set_left_margin(25)
    pdf.set_right_margin(25)

    if candidate_name:
        candidate_name = _sanitize_text(candidate_name)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, candidate_name, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(30, 30, 30)

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        paragraph = paragraph.replace("\n", " ")
        pdf.multi_cell(0, 6, paragraph)
        pdf.ln(4)

    return bytes(pdf.output())
