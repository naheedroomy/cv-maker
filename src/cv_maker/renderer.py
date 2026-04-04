# src/cv_maker/renderer.py
# LaTeX rendering pipeline: TailoredCV -> LaTeX source -> PDF bytes.
# Three public functions: escape_latex(), render_latex(), render_pdf().
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import jinja2

from cv_maker.models import TailoredCV

# ---------------------------------------------------------------------------
# Template environment — custom delimiters to avoid LaTeX {} collision
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_jinja_env = jinja2.Environment(
    block_start_string=r"\BLOCK{",
    block_end_string="}",
    variable_start_string=r"\VAR{",
    variable_end_string="}",
    comment_start_string=r"\#{",
    comment_end_string="}",
    line_statement_prefix="%%",
    line_comment_prefix="%#",
    trim_blocks=True,
    autoescape=False,  # noqa: S701 — MUST be False; HTML escaping corrupts LaTeX backslash commands
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
)

# ---------------------------------------------------------------------------
# LaTeX special character escaping
# ---------------------------------------------------------------------------

# Single-pass lookup: regex matches any special char in one sweep.
# This prevents cascading — e.g. \textbackslash{} having its braces re-escaped.
_LATEX_ESCAPE_CHARS: dict[str, str] = {
    "\\": r"\textbackslash{}",  # backslash — yields \textbackslash{} (braces not re-processed)
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\^{}",
}

# Pre-compile regex matching any of the 10 special characters (single pass).
_LATEX_SPECIAL_RE = re.compile(r"[\\&%$#_{}\~\^]")


def escape_latex(text: str) -> str:
    """Escape all 10 LaTeX-reserved characters in a user-supplied string.

    Uses a single-pass regex substitution to prevent cascading replacements.
    For example, backslash becomes \\textbackslash{} without the {} being
    further escaped in subsequent iterations.

    Apply to every user-supplied string before insertion into a LaTeX template.
    """
    return _LATEX_SPECIAL_RE.sub(lambda m: _LATEX_ESCAPE_CHARS[m.group()], text)


# Register as a Jinja2 filter so templates can call \VAR{value|e}
_jinja_env.filters["e"] = escape_latex

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def escape_latex_with_bold(text: str) -> str:
    """Escape LaTeX special chars but convert **bold** to \\textbf{bold}.

    Splits on **...** markers, escapes each segment, then wraps bold
    segments in \\textbf{}.
    """
    parts = _BOLD_RE.split(text)
    result = []
    for i, part in enumerate(parts):
        escaped = escape_latex(part)
        if i % 2 == 1:  # odd indices are the captured bold groups
            result.append(r"\textbf{" + escaped + "}")
        else:
            result.append(escaped)
    return "".join(result)


_jinja_env.filters["be"] = escape_latex_with_bold

# ---------------------------------------------------------------------------
# latexmk binary discovery (lazy — called only inside render_pdf)
# ---------------------------------------------------------------------------


def _find_latexmk() -> str:
    """Locate latexmk binary or raise FileNotFoundError with install instructions."""
    found = shutil.which("latexmk")
    if found:
        return found
    # macOS: MacTeX default location
    mactex_path = "/Library/TeX/texbin/latexmk"
    if Path(mactex_path).exists():
        return mactex_path
    # Windows: MiKTeX default location
    miktex_path = r"C:\Program Files\MiKTeX\miktex\bin\x64\latexmk.exe"
    if Path(miktex_path).exists():
        return miktex_path
    raise FileNotFoundError(
        "latexmk not found. Install MacTeX (macOS) or MiKTeX (Windows) "
        "and ensure latexmk is on PATH."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_latex(cv: TailoredCV) -> str:
    """Render a TailoredCV object to a LaTeX source string.

    Raises:
        jinja2.TemplateNotFound: if cv.tex.jinja is missing from templates/.
    """
    template = _jinja_env.get_template("cv.tex.jinja")
    return template.render(cv=cv)


def render_pdf(latex_source: str) -> bytes:
    """Compile a LaTeX source string to PDF bytes.

    Uses latexmk with -halt-on-error so compilation failures raise RuntimeError
    rather than silently returning a corrupt PDF.

    Raises:
        FileNotFoundError: if latexmk is not installed.
        RuntimeError: with readable log excerpt on LaTeX compilation failure.
        subprocess.TimeoutExpired: if compilation exceeds 60 seconds.
    """
    latexmk_bin = _find_latexmk()  # Lazy — raises FileNotFoundError if absent
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "cv.tex"
        tex_path.write_text(latex_source, encoding="utf-8")

        # Sanitize PATH: MiKTeX scans each PATH entry as a directory and crashes
        # if it encounters a file (e.g. claude.exe). Keep only real directories.
        env = os.environ.copy()
        if os.name == "nt":
            clean_path = os.pathsep.join(
                p for p in env.get("PATH", "").split(os.pathsep)
                if Path(p).is_dir()
            )
            env["PATH"] = clean_path

        result = subprocess.run(  # noqa: S603
            [
                latexmk_bin,
                "-xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "cv.tex",
            ],
            cwd=tmpdir,
            capture_output=True,
            timeout=60,
            env=env,
        )

        if result.returncode != 0:
            log = result.stdout.decode(errors="replace")
            err = result.stderr.decode(errors="replace")
            combined = log + "\n" + err
            lines = combined.splitlines()
            excerpt = "\n".join(lines[-50:]) if len(lines) > 50 else combined
            raise RuntimeError(f"LaTeX compilation failed:\n{excerpt}")

        return (Path(tmpdir) / "cv.pdf").read_bytes()
