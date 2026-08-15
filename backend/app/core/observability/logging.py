"""Structured JSON logging with structlog and correlation IDs."""

import logging
import sys
from typing import Any

import structlog
from pythonjsonlogger import jsonlogger
from structlog.types import EventDict, WrappedLogger

from app.core.request_id import get_request_id


def add_request_id(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add request ID to log entries when available."""
    request_id = get_request_id()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_service_context(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service context to log entries."""
    event_dict["service"] = "annex-backend"
    event_dict["version"] = "0.1.0"
    return event_dict


def drop_color_message_key(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Remove color_message key from structlog output."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(log_level: str = "INFO", debug: bool = False) -> None:
    """Configure structured JSON logging for production, pretty for development."""

    # Standard library logging config
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Shared processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        add_service_context,
        add_request_id,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        drop_color_message_key,
    ]

    if debug:
        # Pretty printing for development
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # JSON output for production
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Configure standard library loggers to use structlog
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "celery"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class StructuredLogger:
    """Convenience wrapper for common logging patterns."""

    def __init__(self, logger: structlog.stdlib.BoundLogger):
        self._logger = logger

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception(event, **kwargs)

    def bind(self, **kwargs: Any) -> "StructuredLogger":
        return StructuredLogger(self._logger.bind(**kwargs))

    def log_request(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs: Any) -> None:
        """Log HTTP request with standard fields."""
        self._logger.info(
            "http_request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs,
        )

    def log_db_query(self, query: str, duration_ms: float, **kwargs: Any) -> None:
        """Log database query with duration."""
        self._logger.debug("db_query", query=query, duration_ms=duration_ms, **kwargs)

    def log_external_api(self, service: str, endpoint: str, status_code: int, duration_ms: float, **kwargs: Any) -> None:
        """Log external API call."""
        self._logger.info(
            "external_api_call",
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs,
        )

    def log_business_event(self, event_type: str, **kwargs: Any) -> None:
        """Log business/domain events for analytics."""
        self._logger.info(f"business.{event_type}", event_type=event_type, **kwargs)