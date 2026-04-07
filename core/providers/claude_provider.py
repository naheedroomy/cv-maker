# src/cv_maker/providers/claude_provider.py
# ClaudeProvider — thin wrapper around the existing Claude CLI pipeline.
from __future__ import annotations

from core.models import BaseCV, GapItem, TailoredCV
from core.pipeline import run_pipeline
from core.providers.base import BaseProvider


class ClaudeProvider(BaseProvider):
    def __init__(self, cli_model: str = "") -> None:
        self._cli_model = cli_model

    def run(self, base_cv: BaseCV, job_text: str, creativity_level: int = 2) -> tuple[TailoredCV, list[GapItem]]:
        return run_pipeline(base_cv, job_text, creativity_level, cli_model=self._cli_model)
