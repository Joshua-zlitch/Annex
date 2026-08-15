"""Prometheus metrics initialization and utilities."""

from typing import Optional

from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings


_meter_provider: Optional[MeterProvider] = None

# Prometheus metrics (direct, for /metrics endpoint)
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "path"],
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

external_api_duration_seconds = Histogram(
    "external_api_duration_seconds",
    "External API call duration in seconds",
    ["service", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks processed",
    ["task_name", "status"],
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

active_users = Gauge(
    "active_users",
    "Number of active users",
)

analysis_jobs_total = Counter(
    "analysis_jobs_total",
    "Total analysis jobs",
    ["status"],
)

analysis_job_duration_seconds = Histogram(
    "analysis_job_duration_seconds",
    "Analysis job duration in seconds",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit exceeded events",
    ["endpoint"],
)


def init_metrics(settings: Settings) -> None:
    """Initialize OpenTelemetry metrics with Prometheus exporter."""
    global _meter_provider

    if _meter_provider is not None:
        return

    resource = Resource.create({
        "service.name": "annex-backend",
        "service.version": "0.1.0",
        "deployment.environment": settings.app_env,
    })

    # Prometheus metric reader for /metrics endpoint
    prometheus_reader = PrometheusMetricReader()

    # OTLP metric reader (if configured)
    readers = [prometheus_reader]
    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        otlp_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=settings.otel_exporter_otlp_insecure,
            ),
            export_interval_millis=60000,
        )
        readers.append(otlp_reader)

    _meter_provider = MeterProvider(resource=resource, metric_readers=readers)
    metrics.set_meter_provider(_meter_provider)


def get_meter(name: str = "annex-backend") -> metrics.Meter:
    """Get a meter instance."""
    return metrics.get_meter(name)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""

    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path

        # Normalize path (replace path params with placeholders)
        # This is a simple version; in production use route matching
        normalized_path = path

        http_requests_in_progress.labels(method=method, path=normalized_path).inc()

        import time
        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            http_requests_total.labels(
                method=method,
                path=normalized_path,
                status_code=response.status_code,
            ).inc()
            http_request_duration_seconds.labels(
                method=method,
                path=normalized_path,
            ).observe(duration)

            return response
        except Exception:
            duration = time.time() - start_time
            http_requests_total.labels(
                method=method,
                path=normalized_path,
                status_code=500,
            ).inc()
            http_request_duration_seconds.labels(
                method=method,
                path=normalized_path,
            ).observe(duration)
            raise
        finally:
            http_requests_in_progress.labels(method=method, path=normalized_path).dec()


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus /metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Convenience functions for business metrics
def record_http_request(method: str, path: str, status_code: int, duration: float) -> None:
    """Record HTTP request metrics."""
    http_requests_total.labels(method=method, path=path, status_code=status_code).inc()
    http_request_duration_seconds.labels(method=method, path=path).observe(duration)


def record_db_query(operation: str, table: str, duration: float) -> None:
    """Record database query metrics."""
    db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)


def record_external_api(service: str, endpoint: str, duration: float) -> None:
    """Record external API call metrics."""
    external_api_duration_seconds.labels(service=service, endpoint=endpoint).observe(duration)


def record_celery_task(task_name: str, status: str, duration: float) -> None:
    """Record Celery task metrics."""
    celery_tasks_total.labels(task_name=task_name, status=status).inc()
    celery_task_duration_seconds.labels(task_name=task_name).observe(duration)


def record_analysis_job(status: str, duration: float) -> None:
    """Record analysis job metrics."""
    analysis_jobs_total.labels(status=status).inc()
    analysis_job_duration_seconds.observe(duration)


def record_rate_limit_exceeded(endpoint: str) -> None:
    """Record rate limit exceeded event."""
    rate_limit_exceeded_total.labels(endpoint=endpoint).inc()


def set_active_users(count: int) -> None:
    """Set active users gauge."""
    active_users.set(count)