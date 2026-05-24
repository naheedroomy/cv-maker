# core/templates/ — LaTeX Template Codemap

## Responsibility
The `templates/` directory contains the Jinja2 LaTeX template that renders a `TailoredCV` Pydantic model into a professional, printable PDF CV. It is the final stage of the rendering pipeline: `TailoredCV` → Jinja2 → LaTeX source → `latexmk -xelatex` → PDF bytes.

## Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Template View** | `cv.tex.jinja` fed by `render_latex(cv: TailoredCV)` | Clean separation: data model (`TailoredCV`) independent of presentation (LaTeX) |
| **Custom Jinja2 Delimiters** | `\BLOCK{}`, `\VAR{}`, `\#{}`, `%%`, `%#` | Avoids collision with LaTeX's native `{}` brace syntax |
| **Filter Pipeline** | `\|e`, `\|be`, `\|se` Jinja2 filters | LaTeX escaping applied at template level; three escape modes for different contexts |

## Rendering Pipeline Flow

```
TailoredCV (Pydantic model)
  │
  ▼
render_latex()                         # core/renderer.py
  │
  ├─▶ _jinja_env.get_template("cv.tex.jinja")
  ├─▶ template.render(cv=cv)           # Jinja2 rendering
  │
  ▼
LaTeX source string
  │
  ▼
render_pdf(latex_source)               # core/renderer.py
  │
  ├─▶ Write to temp file
  ├─▶ latexmk -xelatex -halt-on-error  # Subprocess call
  │
  ▼
PDF bytes
```

## Template Structure (`cv.tex.jinja`)

The template uses the `moderncv` LaTeX document class with `banking` style and `blue` color theme.

### Document Setup (lines 1–43)
- **Document class**: `moderncv` 11pt, A4 paper, `banking` style, `blue` color scheme
- **Packages**: `geometry` (0.85 scale), `fontspec` (system fonts), `needspace` (widow/orphan prevention), `xcolor` with `dvipsnames`, `tcolorbox` (for pills)
- **Custom `\pill` command**: A `\newtcbox` for core competencies — teal background (12%), rounded corners (4pt), sans-serif small text
- **Contact block**: `\name`, `\email`, conditional `\phone`, `\social[linkedin]` (URL stripped to username), `\social[github]` (URL stripped), `\address`, `\extrainfo` (work authorization)

### Body Sections (lines 44–136)

| Section | Lines | Conditional? | Format |
|---------|-------|-------------|--------|
| Summary | 47–48 | No (always present) | Plain paragraph via `\|se` filter (strip bold + escape) |
| Core Competencies | 50–59 | Yes (if `cv.core_competencies` non-empty) | Pill badges in a `sloppypar`, 4pt spacing |
| Experience | 62–79 | Always (expected non-empty) | `\cventry` per role: date range, title, company, location; `itemize` bullets with `\|be` filter (escape + bold→`\textbf{}`) |
| Certifications | 81–89 | Yes (if `cv.certifications` non-empty) | `itemize` list |
| Education | 91–99 | Always (expected non-empty) | `\cventry` per entry: year, degree, institution, field |
| Skills | 101–105 | Yes (if `cv.skills` non-empty) | Comma-separated string via `\|e` filter |
| Highlighted Technologies | 107–111 | Yes (if `cv.highlighted_technologies` non-empty) | Comma-separated string via `\|e` filter |
| Languages | 113–119 | Yes (if `cv.languages` non-empty) | `\cvitem` per language: name → level |
| Projects | 121–135 | Yes (if `cv.projects` non-empty) | `\cvitem` per project: name → description, optional technologies in italics, optional `\href` URL |

## Three LaTeX Escape Filters

All registered in `core/renderer.py` and available in templates:

| Filter | Name | Behavior | Used For |
|--------|------|----------|----------|
| `\|e` | `escape_latex()` | Single-pass regex escape of 10 LaTeX special chars (`\`, `&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, `^`) | Plain text fields: names, company names, skills, certifications, languages, technologies, URLs |
| `\|be` | `escape_latex_with_bold()` | Escapes LaTeX chars, then converts `**text**` markers → `\textbf{text}` | Experience bullets (AI may emit `**bold**` markers) |
| `\|se` | `escape_latex_strip_bold()` | Strips `**bold**` markers entirely (via `\1` replacement), then escapes LaTeX chars | Summary field (bold formatting not wanted) |

## Key Template Conventions

- **Every user-supplied string MUST use a LaTeX escape filter**. The `%#` comment on line 3 documents this rule.
- **Conditional blocks**: Sections like Core Competencies, Certifications, Skills, Technologies, Languages, and Projects are guarded by `\BLOCK{if cv.X}` blocks — they only render when the field is non-empty.
- **Experience formatting**: Each role gets the `\needspace{5\baselineskip}` command to prevent widows/orphans across page boundaries. Dates use `YYYY-MM -- Present` format when `end` is null.
- **Social media URL stripping**: LinkedIn URLs are stripped to username via Jinja2 `replace()` filter chain (line 32). GitHub URLs similarly stripped (line 35). Performed AFTER LaTeX escaping to avoid corrupting the URL structure.
- **Core competencies pills**: Rendered inline (not as a list) using `\pill{}` boxes separated by `\hspace{4pt}` within a `sloppypar` to allow line wrapping.

## Integration Points

- **`core/renderer.py`**: Owns the Jinja2 `Environment` (`_jinja_env`), registers the escape filters, calls `get_template("cv.tex.jinja")`.
- **`core/models.py`**: The `TailoredCV` model is the single variable passed as `cv` to the template context.
- **`latexmk` binary**: Discovered at render time by `_find_latexmk()` in `renderer.py`; searches PATH, MacTeX default location, and MiKTeX default location. Uses `-xelatex` engine for Unicode/font support.

## Operational Notes

- **Custom delimiters are critical**: Standard Jinja2 `{{ }}` delimiters would collide with LaTeX commands. The `\BLOCK{...}` (blocks), `\VAR{...}` (variables), `\#{...}` (comments), `%%` (line statements), and `%#` (line comments) delimiters avoid all LaTeX conflicts.
- **`autoescape=False` is mandatory**: HTML auto-escaping would corrupt LaTeX backslash commands. The comment `# noqa: S701` acknowledges the security linter exception — user-supplied strings are still manually escaped via filters.
- **`trim_blocks=True`**: Strips trailing newlines after block tags, keeping the generated LaTeX source clean.
- **Single-pass escaping**: `escape_latex()` compiles one regex (`[\\&%$#_{}\~\^]`) and substitutes in one pass — prevents cascading where `\textbackslash{}` braces get re-escaped.
- **PDF failure detection**: `latexmk` runs with `-halt-on-error`, so compilation failures raise `RuntimeError` with the last 50 lines of the log rather than silently returning a corrupt PDF.
