from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any


class BackgroundJobRunner(ABC):
    """Schedules fire-and-forget coroutines (FastAPI BackgroundTasks in Phase 1)."""

    @abstractmethod
    def run_in_background(self, coroutine: Coroutine[Any, Any, Any]) -> None:
        """Schedule ``coroutine`` to run after the current request completes."""
