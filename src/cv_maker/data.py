# src/cv_maker/data.py
# YAML loader for base_cv.yaml with Pydantic v2 validation.
# Source: Pydantic v2 docs — https://docs.pydantic.dev/latest/concepts/models/
import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from cv_maker.models import BaseCV

DEFAULT_CV_PATH = Path(os.environ.get("BASE_CV_PATH", "base_cv.yaml"))


def ensure_base_cv_exists(path: Path = DEFAULT_CV_PATH) -> None:
    """Create an empty base_cv.yaml with placeholder structure if it doesn't exist."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    placeholder = {
        "contact": {
            "name": "",
            "email": "",
            "linkedin": None,
            "github": None,
            "phone": None,
            "location": None,
        },
        "summary": "",
        "experience": [],
        "skills": [],
        "education": [],
        "projects": [],
        "certifications": [],
    }
    import yaml as _yaml

    with open(path, "w", encoding="utf-8") as f:
        _yaml.dump(placeholder, f, default_flow_style=False, allow_unicode=True)


def load_base_cv(path: Path = DEFAULT_CV_PATH) -> BaseCV:
    """Load and validate the base CV YAML file.

    Raises:
        FileNotFoundError: if the path does not exist.
        RuntimeError: if the YAML is not a mapping or fails Pydantic validation.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Base CV not found at: {path}. Use the Import CV page to create one."
        )

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)  # safe_load: never executes arbitrary Python objects (Ruff S506)

    if not isinstance(raw, dict):
        raise RuntimeError(
            f"base_cv.yaml must be a YAML mapping at the top level, got: {type(raw).__name__}"
        )

    try:
        return BaseCV.model_validate(raw)
    except ValidationError as e:
        # Surface all field errors at once — don't stop at first failure.
        # Prefix matches what Phase 4 Streamlit error handler will check for.
        raise RuntimeError(f"base_cv.yaml failed validation:\n{e}") from e
