# src/cv_maker/data.py
# YAML loader for base_cv.yaml with Pydantic v2 validation.
# Source: Pydantic v2 docs — https://docs.pydantic.dev/latest/concepts/models/
from pathlib import Path

import yaml
from pydantic import ValidationError

from cv_maker.models import BaseCV

DEFAULT_CV_PATH = Path("base_cv.yaml")


def load_base_cv(path: Path = DEFAULT_CV_PATH) -> BaseCV:
    """Load and validate the base CV YAML file.

    Raises:
        FileNotFoundError: if the path does not exist.
        RuntimeError: if the YAML is not a mapping or fails Pydantic validation.
            Message always starts with "base_cv.yaml failed validation:" for
            consistent error handling in the Streamlit UI (Phase 4).
    """
    if not path.exists():
        raise FileNotFoundError(f"Base CV not found at: {path}")

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
