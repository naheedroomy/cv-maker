# src/cv_maker/providers/claude_provider.py
# ClaudeProvider — thin wrapper around the existing Claude CLI pipeline.
from __future__ import annotations

from core.models import BaseCV, GapItem, TailoredCV
from core.pipeline import _invoke_claude, run_pipeline, run_pipeline_staged
from core.providers.base import BaseProvider


class ClaudeProvider(BaseProvider):
    def __init__(self, cli_model: str = "") -> None:
        self._cli_model = cli_model

    def run(self, base_cv: BaseCV, job_text: str, creativity_level: int = 2, user_notes: str = "") -> tuple[TailoredCV, list[GapItem]]:
        return run_pipeline(base_cv, job_text, creativity_level, cli_model=self._cli_model, user_notes=user_notes)

    def run_staged(
        self, base_cv: BaseCV, job_text: str, creativity_level: int = 2, user_notes: str = ""
    ) -> tuple[TailoredCV, list[GapItem]]:
        """Multi-stage pipeline via claude -p, one CLI invocation per stage."""

        def _call(prompt: str) -> str:
            return _invoke_claude(prompt, cli_model=self._cli_model)

        return run_pipeline_staged(
            base_cv, job_text, _call,
            creativity_level=creativity_level, user_notes=user_notes,
        )
