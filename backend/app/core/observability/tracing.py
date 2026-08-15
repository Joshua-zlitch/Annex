"""OpenTelemetry tracing initialization and utilities."""

from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import Settings


_tracer_provider: Optional[TracerProvider] = None


def init_tracing(settings: Settings) -> None:
    """Initialize OpenTelemetry tracing with OTLP exporter."""
    global _tracer_provider

    if _tracer_provider is not None:
        return  # Already initialized

    resource = Resource.create({
        "service.name": "annex-backend",
        "service.version": "0.1.0",
        "deployment.environment": settings.app_env,
    })

    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)

    # OTLP exporter (to Tempo/Jaeger/Collector)
    if settings.otel_exporter_otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=settings.otel_exporter_otlp_insecure,
        )
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Auto-instrument libraries
    FastAPIInstrumentor.instrument()
    PsycopgInstrumentor.instrument()
    RedisInstrumentor.instrument()
    CeleryInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()

    # Note: For SQLAlchemy, use SQLAlchemyInstrumentor if using SQLAlchemy


def get_tracer(name: str = "annex-backend") -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)


def get_current_span() -> trace.Span:
    """Get the current active span."""
    return trace.get_current_span()


def add_span_attributes(attributes: dict[str, str | int | float | bool]) -> None:
    """Add attributes to the current span."""
    span = get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def record_exception(exception: Exception, attributes: dict[str, str | int | float | bool] | None = None) -> None:
    """Record an exception on the current span."""
    span = get_current_span()
    if span.is_recording():
        span.record_exception(exception)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)