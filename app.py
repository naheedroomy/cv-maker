from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from cv_maker.data import load_base_cv
from cv_maker.models import GapItem, TailoredCV
from cv_maker.pipeline import run_pipeline
from cv_maker.renderer import render_latex, render_pdf

st.set_page_config(page_title="CV Maker", layout="centered")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HISTORY_DIR = Path.home() / ".cv-maker" / "history"
OUTPUT_DIR = Path("output")


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------


def _save_history(
    job_text: str,
    role_title: str,
    tailored_cv: TailoredCV,
    gap_diff: list[GapItem],
    company_name: str = "",
    job_link: str = "",
) -> None:
    """Persist a completed run to ~/.cv-maker/history/ as a timestamped JSON file."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    slug = "".join(c if c.isalnum() else "-" for c in role_title.lower())[:40]
    target = HISTORY_DIR / f"{ts}-{slug}.json"
    record = {
        "timestamp": ts,
        "role_title": role_title,
        "company_name": company_name,
        "job_link": job_link,
        "job_text": job_text,
        "tailored_cv": tailored_cv.model_dump(),
        "gap_diff": [g.model_dump() for g in gap_diff],
    }
    target.write_text(json.dumps(record, indent=2), encoding="utf-8")


def _load_history_index() -> list[dict]:
    """Return list of history records sorted newest-first. Corrupt files are skipped."""
    if not HISTORY_DIR.exists():
        return []
    records = []
    for f in sorted(HISTORY_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            label = f"{data.get('role_title', 'Unknown')} — {data.get('timestamp', '')}"
            records.append({"path": str(f), "label": label, "data": data})
        except (json.JSONDecodeError, KeyError):
            pass  # Skip corrupt files silently
    return records


# ---------------------------------------------------------------------------
# Base CV loading — cached; stop on failure
# ---------------------------------------------------------------------------


@st.cache_data
def _load_cv():
    try:
        return load_base_cv()
    except (FileNotFoundError, RuntimeError) as exc:
        st.error(str(exc))
        st.stop()


base_cv = _load_cv()

# ---------------------------------------------------------------------------
# Session state initialisation (before any widgets)
# ---------------------------------------------------------------------------

if "result" not in st.session_state:
    st.session_state["result"] = None
if "pdf_bytes" not in st.session_state:
    st.session_state["pdf_bytes"] = None
if "pdf_path" not in st.session_state:
    st.session_state["pdf_path"] = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_gap_table(gap_diff: list[GapItem]) -> None:
    st.subheader("Gap Analysis")
    rows = [
        {
            "Requirement": g.requirement,
            "Present": "Yes" if g.present else "No",
            "Evidence": g.evidence or "—",
        }
        for g in gap_diff
    ]
    df = pd.DataFrame(rows)

    def _color_row(row):
        color = "#d4edda" if row["Present"] == "Yes" else "#f8d7da"
        return [f"background-color: {color}"] * len(row)

    st.dataframe(df.style.apply(_color_row, axis=1), use_container_width=True, hide_index=True)


def _render_cv_preview(cv: TailoredCV) -> None:
    st.subheader("Tailored CV Preview")
    st.markdown(f"**{cv.contact.name}** | {cv.contact.email}")
    if cv.contact.linkedin:
        st.markdown(f"LinkedIn: {cv.contact.linkedin}")
    if cv.contact.location:
        st.markdown(f"Location: {cv.contact.location}")
    st.markdown("---")
    st.markdown("### Summary")
    st.write(cv.summary)
    st.markdown("### Experience")
    for exp in cv.experience:
        end_str = exp.end or "Present"
        st.markdown(f"**{exp.title}** at {exp.company} ({exp.start} – {end_str})")
        for bullet in exp.bullets:
            st.markdown(f"- {bullet}")
        if exp.technologies:
            st.caption(f"Technologies: {', '.join(exp.technologies)}")
    st.markdown("### Skills")
    st.write(", ".join(cv.skills))
    if cv.highlighted_technologies:
        st.markdown("### Highlighted Technologies")
        st.write(", ".join(cv.highlighted_technologies))
    if cv.education:
        st.markdown("### Education")
        for edu in cv.education:
            field_str = f", {edu.field}" if edu.field else ""
            year_str = f" ({edu.year})" if edu.year else ""
            st.markdown(f"**{edu.degree}{field_str}** — {edu.institution}{year_str}")
    if cv.certifications:
        st.markdown("### Certifications")
        for cert in cv.certifications:
            st.markdown(f"- {cert}")


# ---------------------------------------------------------------------------
# Sidebar — session list
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Sessions")

    # New button — clears current session state to start fresh
    if st.button("+ New", use_container_width=True):
        st.session_state["result"] = None
        st.session_state["pdf_bytes"] = None
        st.session_state["pdf_path"] = None
        st.session_state.pop("active_history_path", None)
        st.rerun()

    st.divider()

    history = _load_history_index()
    if history:
        active_path = st.session_state.get("active_history_path")
        for h in history:
            # Label: use company_name if present in record, else fall back to role_title
            record = h["data"]
            company = record.get("company_name", "")
            role = record.get("role_title", "Unknown")
            label = f"{company} — {role}" if company else role
            ts = record.get("timestamp", "")
            # Truncate timestamp to readable date portion
            date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ts

            is_active = (h["path"] == active_path)
            btn_label = f"**{label}**\n{date_str}" if is_active else f"{label}\n{date_str}"

            if st.button(btn_label, key=h["path"], use_container_width=True):
                chosen = h["data"]
                st.session_state["result"] = {
                    "tailored_cv": TailoredCV.model_validate(chosen["tailored_cv"]),
                    "gap_diff": [GapItem.model_validate(g) for g in chosen["gap_diff"]],
                }
                st.session_state["pdf_bytes"] = None
                st.session_state["pdf_path"] = None
                st.session_state["active_history_path"] = h["path"]
                st.rerun()
    else:
        st.caption("No past sessions yet.")

# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

st.title("CV Maker")
st.caption("Paste a job listing and click Generate to tailor your CV.")

company_name = st.text_input("Company Name", placeholder="e.g. Acme Corp")
job_link = st.text_input("Job Listing URL (optional)", placeholder="https://...")
job_text = st.text_area("Job Listing", height=300, placeholder="Paste the job listing here...")

if st.button("Generate Tailored CV", type="primary"):
    if not job_text.strip() or not company_name.strip():
        st.warning("Please enter a company name and paste a job listing before generating.")
    else:
        try:
            with st.spinner("Analysing job listing and tailoring CV...", show_time=True):
                tailored_cv, gap_diff = run_pipeline(base_cv, job_text)
            with st.spinner("Compiling PDF...", show_time=True):
                pdf_bytes = render_pdf(render_latex(tailored_cv))
            # Auto-save PDF to output/{company_slug}/CV-{ApplicantName}.pdf
            company_slug = "".join(
                c if c.isalnum() or c in " -_" else "" for c in company_name
            ).strip().replace(" ", "-")
            applicant_name = tailored_cv.contact.name.replace(" ", "")
            pdf_dir = OUTPUT_DIR / company_slug
            pdf_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = pdf_dir / f"CV-{applicant_name}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            st.session_state["result"] = {"tailored_cv": tailored_cv, "gap_diff": gap_diff}
            st.session_state["pdf_bytes"] = None
            st.session_state["pdf_path"] = str(pdf_path)
            role_label = (
                job_text.strip().splitlines()[0][:40] if job_text.strip() else "Unknown Role"
            )
            _save_history(
                job_text=job_text,
                role_title=role_label,
                tailored_cv=tailored_cv,
                gap_diff=gap_diff,
                company_name=company_name,
                job_link=job_link,
            )
        except RuntimeError as exc:
            st.error(f"Generation failed: {exc}")

# ---------------------------------------------------------------------------
# Results section — reads only from session_state, never calls pipeline
# ---------------------------------------------------------------------------

if st.session_state["result"] is not None:
    result = st.session_state["result"]
    _render_gap_table(result["gap_diff"])
    st.divider()
    _render_cv_preview(result["tailored_cv"])
    st.divider()
    if st.session_state.get("pdf_path"):
        st.success(f"PDF saved to: {st.session_state['pdf_path']}")
