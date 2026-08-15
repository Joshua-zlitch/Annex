"""Application settings loaded from environment variables.

Configuration follows the Twelve-Factor model: every value is overridable
via environment variables (optionally sourced from a local ``.env`` file)
and never hardcoded in application code. The cached instance is provided
through ``get_settings()`` so tests can build their own ``Settings``.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__

# ``backend/`` — anchored to the module so .env resolution does not depend
# on the process working directory.
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Runtime environments the service can run in.
AppEnv = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    """Runtime configuration for the ANNEX backend.

    Values are read from environment variables (case-insensitive) and from
    a ``backend/.env`` file when present. Unknown environment variables are
    ignored so shared environments do not break the service.
    """

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Product identity.
    app_name: str = "ANNEX API"
    app_version: str = __version__

    # Runtime behavior.
    app_env: AppEnv = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API surface.
    api_v1_prefix: str = "/api/v1"

    # Database (Phase 4): direct PostgreSQL endpoint (Supabase local or
    # pooled production URL). None disables DB-backed repositories and
    # readiness checks.
    database_url: str | None = None

    # Authentication (Phase 5): Firebase project + Admin SDK service account.
    # None disables the token verifier (protected routes answer 503).
    firebase_project_id: str | None = None
    firebase_service_account_path: str | None = None

    # AI providers (Phase 6): claim analysis. At least one key enables the
    # analyzer; Gemini is optional (ADR-0006).
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # OCR (Phase 6): Tesseract language codes.
    ocr_languages: str = "eng"

    # Media analysis (Phase 13): URL fetching (SSRF-guarded) and image
    # submission limits. Fetch timeouts/limits keep the worker from being
    # dragged into slow or unbounded downloads; image submissions are
    # capped in decoded byte size at the API boundary.
    media_fetch_timeout: float = 10.0
    media_fetch_max_bytes: int = 2_000_000
    media_image_max_bytes: int = 4_000_000

    # Async pipelines (Phase 7, ADR-0008): Redis URL used by the rate
    # limiter and readiness probe; Celery broker/result endpoints for the
    # analysis worker. Broker/backend fall back to the Redis URL so a
    # single local Redis instance covers development.
    redis_url: str | None = None
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # Rate limiting (Phase 7): fixed-window counters per client, expressed
    # as "<count>/<unit>" (second | minute | hour | day).
    rate_limit_default: str = "120/minute"
    rate_limit_analysis: str = "20/minute"

    # Runtime i18n (Phase 8, ADR-0007): the fallback-chain root and the
    # Cache-Control TTL (seconds) for locale bundles served to clients.
    i18n_default_locale: str = "en"
    i18n_bundle_cache_ttl: int = 300

    # CORS: origins allowed to call the API from browsers.
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )

    # Observability (Phase 4): Sentry, OpenTelemetry, Prometheus.
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.1

    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_insecure: bool = False

    # Prometheus metrics endpoint (enabled by default in non-prod)
    metrics_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached settings (parsed once)."""
    return Settings()
