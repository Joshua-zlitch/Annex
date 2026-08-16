from __future__ import annotations

import asyncio

from app.infrastructure.container import Container
from app.infrastructure.jobs.celery_app import celery_app


@celery_app.task(name="app.jobs.analyze_media", bind=True, max_retries=3, soft_time_limit=600)
def analyze_media_task(self, analysis_id: str) -> None:
    """Run the media analysis pipeline in a Celery worker (async-safe wrapper)."""
    asyncio.run(_run(analysis_id))


async def _run(analysis_id: str) -> None:
    container = Container.build()
    await container.analyze_media_use_case.execute(analysis_id)
