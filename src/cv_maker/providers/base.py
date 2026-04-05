# src/cv_maker/providers/base.py
# Abstract base class defining the provider interface (Strategy pattern).
from __future__ import annotations

from abc import ABC, abstractmethod

from cv_maker.models import BaseCV, GapItem, TailoredCV


class BaseProvider(ABC):
    @abstractmethod
    def run(self, base_cv: BaseCV, job_text: str) -> tuple[TailoredCV, list[GapItem]]:
        """Run the CV tailoring pipeline. Returns (tailored_cv, gap_diff)."""
        ...
