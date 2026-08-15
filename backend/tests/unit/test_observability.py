"""Tests for observability module."""

import pytest
from unittest.mock import patch, MagicMock

from app.core.observability import (
    configure_logging,
    get_logger,
    init_tracing,
    get_tracer,
    init_metrics,
    get_meter,
    init_sentry,
)
from app.core.config import Settings


class TestObservabilityLogging:
    """Tests for structured logging."""

    def test_configure_logging_debug(self):
        """Test logging configuration in debug mode."""
        configure_logging("DEBUG", debug=True)
        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_production(self):
        """Test logging configuration in production mode."""
        configure_logging("INFO", debug=False)
        logger = get_logger("test")
        assert logger is not None

    def test_get_logger_returns_bound_logger(self):
        """Test that get_logger returns a bound logger."""
        logger = get_logger("test.module")
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")


class TestObservabilityTracing:
    """Tests for OpenTelemetry tracing."""

    def test_init_tracing_without_endpoint(self):
        """Test tracing initialization without OTLP endpoint."""
        settings = Settings(
            _env_file=None,
            app_env="test",
            otel_exporter_otlp_endpoint=None,
        )
        init_tracing(settings)
        tracer = get_tracer("test")
        assert tracer is not None

    def test_get_tracer_returns_tracer(self):
        """Test that get_tracer returns a tracer."""
        tracer = get_tracer("test.module")
        assert tracer is not None
        assert hasattr(tracer, "start_span")


class TestObservabilityMetrics:
    """Tests for Prometheus metrics."""

    def test_init_metrics(self):
        """Test metrics initialization."""
        settings = Settings(_env_file=None, app_env="test")
        init_metrics(settings)
        meter = get_meter("test")
        assert meter is not None
        assert hasattr(meter, "create_counter")
        assert hasattr(meter, "create_histogram")

    def test_metrics_middleware_exists(self):
        """Test that metrics middleware is importable."""
        from app.core.observability import metrics_middleware
        assert metrics_middleware is not None


class TestObservabilitySentry:
    """Tests for Sentry initialization."""

    def test_init_sentry_without_dsn(self):
        """Test Sentry initialization without DSN (should not fail)."""
        settings = Settings(_env_file=None, app_env="test", sentry_dsn=None)
        # Should not raise
        init_sentry(settings)

    def test_init_sentry_with_dsn(self):
        """Test Sentry initialization with DSN."""
        settings = Settings(
            _env_file=None,
            app_env="test",
            sentry_dsn="https://test@sentry.io/123",
        )
        with patch("sentry_sdk.init") as mock_init:
            init_sentry(settings)
            mock_init.assert_called_once()


class TestObservabilityIntegration:
    """Integration tests for observability."""

    def test_full_initialization(self):
        """Test full observability stack initialization."""
        settings = Settings(
            _env_file=None,
            app_env="test",
            otel_exporter_otlp_endpoint=None,
            sentry_dsn=None,
        )

        # Should not raise any exceptions
        configure_logging("INFO", debug=False)
        init_tracing(settings)
        init_metrics(settings)
        init_sentry(settings)

        # Verify all components accessible
        logger = get_logger("integration.test")
        tracer = get_tracer("integration.test")
        meter = get_meter("integration.test")

        assert logger is not None
        assert tracer is not None
        assert meter is not None

    def test_structured_logger_methods(self):
        """Test structured logger convenience methods."""
        configure_logging("DEBUG", debug=True)
        from app.core.observability.logging import StructuredLogger

        logger = get_logger("test")
        structured = StructuredLogger(logger)

        # These should not raise
        structured.info("test event", key="value")
        structured.warning("warning event")
        structured.error("error event")
        structured.debug("debug event")
        structured.log_request("GET", "/api/test", 200, 15.5)
        structured.log_db_query("SELECT * FROM users", 2.3)
        structured.log_external_api("openai", "/v1/chat/completions", 200, 150.0)
        structured.log_business_event("analysis_completed", analysis_id="123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])