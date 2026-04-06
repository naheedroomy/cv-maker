# src/cv_maker/providers/claude_provider.py
# ClaudeProvider — thin wrapper around the existing Claude CLI pipeline.
from __future__ import annotations

from cv_maker.models import BaseCV, GapItem, TailoredCV
from cv_maker.pipeline import run_pipeline
from cv_maker.providers.base import BaseProvider


class ClaudeProvider(BaseProvider):
    def run(self, base_cv: BaseCV, job_text: str, creativity_level: int = 2) -> tuple[TailoredCV, list[GapItem]]:
        return run_pipeline(base_cv, job_text, creativity_level)
