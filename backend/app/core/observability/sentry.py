"""Sentry error tracking initialization."""

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config import Settings


def init_sentry(settings: Settings) -> None:
    """Initialize Sentry SDK with FastAPI, Celery, Redis, and SQLAlchemy integrations."""
    if not settings.sentry_dsn:
        return

    sentry_logging = LoggingIntegration(
        level=None,  # Capture all levels
        event_level=None,  # Send all as events
    )

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=settings.app_version,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={400, 401, 403, 404, 500, 502, 503, 504},
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
            RedisIntegration(),
            SqlalchemyIntegration(),
            sentry_logging,
        ],
        # Filter out health check noise
        before_send=lambda event, hint: _filter_events(event, hint),
        # Attach request data
        send_default_pii=True,
        # Performance monitoring
        enable_tracing=True,
    )


def _filter_events(event: dict, hint: dict) -> dict | None:
    """Filter out noisy events before sending to Sentry."""
    # Drop health check requests
    if event.get("request", {}).get("url", "").endswith(("/health", "/health/ready", "/metrics")):
        return None

    # Drop favicon requests
    if event.get("request", {}).get("url", "").endswith("/favicon.ico"):
        return None

    return event


def capture_exception(exc: Exception, context: dict | None = None) -> str:
    """Capture an exception and return the event ID."""
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_extra(key, value)
        return sentry_sdk.capture_exception(exc)


def capture_message(message: str, level: str = "info", context: dict | None = None) -> str:
    """Capture a message and return the event ID."""
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_extra(key, value)
        return sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: str | None = None, username: str | None = None) -> None:
    """Set user context for Sentry."""
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "username": username,
    })


def clear_user_context() -> None:
    """Clear user context."""
    sentry_sdk.set_user(None)


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: dict | None = None,
) -> None:
    """Add a breadcrumb for debugging."""
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )