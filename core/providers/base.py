# src/cv_maker/providers/base.py
# Abstract base class defining the provider interface (Strategy pattern).
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from core.models import BaseCV, GapItem, TailoredCV

# Provider callable type: takes a prompt string, returns raw text output.
ProviderFn = Callable[[str], str]


class BaseProvider(ABC):
    @abstractmethod
    def run(self, base_cv: BaseCV, job_text: str, creativity_level: int = 2, user_notes: str = "") -> tuple[TailoredCV, list[GapItem]]:
        """Run the CV tailoring pipeline. Returns (tailored_cv, gap_diff)."""
        ...
