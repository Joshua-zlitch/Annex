from __future__ import annotations

from collections.abc import Coroutine
from typing import Any

from fastapi import BackgroundTasks

from app.core.ports.jobs import BackgroundJobRunner


async def _await_coroutine(coroutine: Coroutine[Any, Any, Any]) -> None:
    await coroutine


class FastAPIBackgroundRunner(BackgroundJobRunner):
    """Schedules coroutines with FastAPI's per-request ``BackgroundTasks``.

    The scheduled coroutine runs on the same event loop after the HTTP response
    is sent (no Redis / Celery needed in Phase 1).
    """

    def __init__(self, background_tasks: BackgroundTasks):
        self._background_tasks = background_tasks

    def run_in_background(self, coroutine: Coroutine[Any, Any, Any]) -> None:
        self._background_tasks.add_task(_await_coroutine, coroutine)
