from __future__ import annotations

from celery import Celery

from app.infrastructure.config import get_settings

celery_app = Celery(
    "annex",
    broker=get_settings().redis_url,
    backend=get_settings().redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
