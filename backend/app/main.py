"""Application factory and entry point.

Wires the application core per ADR-0003: configuration, structured
logging, request-ID tracing, the error envelope, CORS, the versioned
router, and the infrastructure ports (database repositories, token
verifier, claim analyzer, media adapters, Celery task dispatcher, rate
limiter) bound to ``app.state`` for dependency injection.
"""

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.application.ports.ai import ClaimAnalyzer
from app.application.ports.auth import TokenVerifier
from app.application.ports.media import ForensicsAdapter, OcrAdapter
from app.application.services.analysis_service import AnalysisService
from app.application.services.claims_service import ClaimsService
from app.application.services.class_service import ClassService
from app.application.services.education_service import EducationService
from app.application.services.i18n_service import I18nService
from app.application.services.media_pipeline import MediaPipeline
from app.application.services.media_service import MediaService
from app.application.services.source_service import SourceService
from app.application.services.translation_suggestion_service import (
    TranslationSuggestionService,
)
from app.application.services.user_service import UserService
from app.core.checks import DatabaseHealthCheck, DependencyCheck, RedisHealthCheck
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.observability import (
    configure_logging as configure_structured_logging,
    init_sentry,
    init_tracing,
    init_metrics,
    metrics_middleware,
    metrics_endpoint,
)
from app.core.request_id import RequestIdMiddleware
from app.infrastructure.ai.factory import build_claim_analyzer
from app.infrastructure.auth.firebase_token_verifier import FirebaseTokenVerifier
from app.infrastructure.media.factory import (
    build_forensics_adapter,
    build_media_pipeline,
    build_ocr_adapter,
)
from app.infrastructure.rate_limit.factory import build_rate_limiter
from app.infrastructure.rate_limit.limiter import RateLimiter
from app.infrastructure.rate_limit.middleware import RateLimitMiddleware
from app.infrastructure.repositories.analysis_repository import PostgresAnalysisRepository
from app.infrastructure.repositories.claim_repository import PostgresClaimRepository
from app.infrastructure.repositories.class_repository import PostgresClassRepository
from app.infrastructure.repositories.i18n_repository import PostgresI18nRepository
from app.infrastructure.repositories.lesson_repository import PostgresLessonRepository
from app.infrastructure.repositories.media_repository import PostgresMediaRepository
from app.infrastructure.repositories.source_repository import PostgresSourceRepository
from app.infrastructure.repositories.translation_suggestion_repository import (
    PostgresTranslationSuggestionRepository,
)
from app.infrastructure.repositories.user_repository import PostgresUserRepository
from app.infrastructure.tasks.dispatcher import build_analysis_task_dispatcher


def create_app(
    settings: Settings | None = None,
    *,
    token_verifier: TokenVerifier | None = None,
    user_service: UserService | None = None,
    claim_analyzer: ClaimAnalyzer | None = None,
    ocr_adapter: OcrAdapter | None = None,
    forensics_adapter: ForensicsAdapter | None = None,
    media_pipeline: MediaPipeline | None = None,
    analysis_service: AnalysisService | None = None,
    claims_service: ClaimsService | None = None,
    source_service: SourceService | None = None,
    media_service: MediaService | None = None,
    education_service: EducationService | None = None,
    class_service: ClassService | None = None,
    i18n_service: I18nService | None = None,
    translation_suggestion_service: TranslationSuggestionService | None = None,
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Args:
        settings: Optional settings override (used by tests); defaults to
            the process-wide cached environment settings.
        token_verifier: Optional verifier override (tests use the mock);
            defaults to a Firebase verifier when Firebase is configured.
        user_service: Optional user service override (tests use mocks);
            defaults to the PostgreSQL-backed service when a database is
            configured.
        claim_analyzer: Optional analyzer override (tests use mocks);
            defaults to the provider selected from settings (ADR-0006).
        ocr_adapter: Optional OCR override; defaults to Tesseract with a
            mock fallback when the binary is missing.
        forensics_adapter: Optional forensics override; defaults to OpenCV.
        media_pipeline: Optional media pipeline override (tests inject
            mocks); defaults to the SSRF-guarded URL fetcher + the bound
            OCR/forensics adapters (Phase 13).
        analysis_service: Optional analysis service override (tests use the
            in-memory repository); defaults to the PostgreSQL-backed service
            when a database is configured, enqueuing work on the Celery
            worker when a broker is configured (ADR-0008).
        claims_service: Optional claims service override (tests use the
            in-memory repository); defaults to the PostgreSQL-backed service
            when a database is configured (Phase 14).
        source_service: Optional source service override; defaults to the
            PostgreSQL-backed service when a database is configured
            (Phase 14).
        media_service: Optional media service override; defaults to the
            PostgreSQL-backed service bound to the media adapters when a
            database is configured (Phase 14).
        education_service: Optional education service override (tests use
            the in-memory repository); defaults to the PostgreSQL-backed
            service when a database is configured (Phase 15).
        class_service: Optional class service override (tests use the
            in-memory repository); defaults to the PostgreSQL-backed service
            when a database is configured (Phase 17).
        i18n_service: Optional i18n service override (tests use the
            in-memory repository); defaults to the PostgreSQL-backed service
            when a database is configured (ADR-0007).
        translation_suggestion_service: Optional suggestion service override
            (tests use the in-memory repository); defaults to the
            PostgreSQL-backed service when a database is configured
            (Phase 18).
        rate_limiter: Optional rate limiter override (tests inject a
            deterministic limiter); defaults to a Redis-backed limiter when
            Redis is configured, else a no-op fallback.

    Returns:
        A fully wired FastAPI application.
    """
    settings = settings or get_settings()
    configure_structured_logging(settings.log_level, debug=settings.debug)

    # Initialize observability (Sentry, OpenTelemetry, Prometheus)
    init_sentry(settings)
    init_tracing(settings)
    init_metrics(settings)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        # The interactive docs UI is a development affordance only.
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
    )

    # Prometheus metrics endpoint
    if settings.metrics_enabled:
        app.add_middleware(metrics_middleware)
        app.add_route("/metrics", metrics_endpoint, methods=["GET"])
    # Bind the settings instance to the app so routes resolve the same
    # configuration object through DI (see app.api.deps).
    app.state.settings = settings

    # Readiness probes registered from settings (database: Phase 4,
    # Redis: Phase 7). Served by GET /health/ready.
    checks: list[DependencyCheck] = []
    if settings.database_url:
        checks.append(DatabaseHealthCheck(settings.database_url))

    # Async pipeline infrastructure (Phase 7, ADR-0008): a shared Redis
    # client backs the readiness probe and the rate limiter when configured.
    redis_client = redis.Redis.from_url(settings.redis_url) if settings.redis_url else None
    app.state.redis = redis_client
    if redis_client is not None:
        checks.append(RedisHealthCheck(redis_client))
    app.state.checks = checks

    # Authentication (ADR-0005): wire the token verifier and the user
    # hydration service from settings unless overridden (tests).
    if token_verifier is None and settings.firebase_project_id:
        token_verifier = FirebaseTokenVerifier(
            settings.firebase_project_id,
            settings.firebase_service_account_path,
        )
    if user_service is None and token_verifier is not None and settings.database_url:
        user_service = UserService(PostgresUserRepository(settings.database_url))
    app.state.token_verifier = token_verifier
    app.state.user_service = user_service

    # AI + media processing (Phase 6, ADR-0006): bind the configured claim
    # analyzer and media adapters to the app so services and endpoints resolve
    # them through DI instead of constructing providers ad hoc. Provider
    # selection is configuration-driven; unconfigured providers fall back to
    # the explicit mocks (local development / tests).
    app.state.claim_analyzer = claim_analyzer or build_claim_analyzer(settings)
    app.state.ocr_adapter = ocr_adapter or build_ocr_adapter(settings)
    app.state.forensics_adapter = forensics_adapter or build_forensics_adapter()
    app.state.media_pipeline = media_pipeline or build_media_pipeline(
        settings,
        ocr_adapter=app.state.ocr_adapter,
        forensics_adapter=app.state.forensics_adapter,
    )

    # Analysis pipeline (Phase 4 domain + Phase 6 API + Phase 7 workers):
    # wire the service from settings unless overridden (tests inject the
    # in-memory mock). With a broker configured the service enqueues work
    # for the Celery worker (ADR-0008); without one it keeps the interim
    # synchronous path.
    task_dispatcher = build_analysis_task_dispatcher(settings)
    app.state.analysis_task_dispatcher = task_dispatcher
    if analysis_service is None and settings.database_url:
        analysis_service = AnalysisService(
            PostgresAnalysisRepository(settings.database_url),
            task_dispatcher=task_dispatcher,
            media_pipeline=app.state.media_pipeline,
            claims_service=ClaimsService(
                PostgresClaimRepository(settings.database_url)
            ),
        )
    app.state.analysis_service = analysis_service

    # Phase 14 domain services: claims (persisted from completed analyses),
    # the public sources registry, and the media library. Each defaults to
    # the PostgreSQL-backed service when a database is configured.
    if claims_service is None and settings.database_url:
        claims_service = ClaimsService(
            PostgresClaimRepository(settings.database_url)
        )
    app.state.claims_service = claims_service
    if source_service is None and settings.database_url:
        source_service = SourceService(PostgresSourceRepository(settings.database_url))
    app.state.source_service = source_service
    if media_service is None and settings.database_url:
        media_service = MediaService(
            PostgresMediaRepository(settings.database_url),
            ocr_adapter=app.state.ocr_adapter,
            forensics_adapter=app.state.forensics_adapter,
        )
    app.state.media_service = media_service

    # Education curriculum (Phase 15): the media-literacy lessons service
    # resolves localized content through the i18n locale registry (ADR-0007)
    # so lesson reads honor the same fallback chain as translation bundles.
    if education_service is None and settings.database_url:
        education_service = EducationService(
            PostgresLessonRepository(settings.database_url),
            PostgresI18nRepository(settings.database_url),
            default_locale=settings.i18n_default_locale,
        )
    app.state.education_service = education_service

    # Educator tools (Phase 17): classes, membership, and lesson
    # assignments. Progress is derived from lesson_progress (Phase 15), so
    # the class service needs only its own persistence port.
    if class_service is None and settings.database_url:
        class_service = ClassService(PostgresClassRepository(settings.database_url))
    app.state.class_service = class_service

    # Runtime i18n (Phase 8, ADR-0007): serve enabled locales and
    # versioned translation bundles from the configured database unless
    # overridden (tests inject the in-memory mock).
    if i18n_service is None and settings.database_url:
        i18n_service = I18nService(
            PostgresI18nRepository(settings.database_url),
            default_locale=settings.i18n_default_locale,
        )
    app.state.i18n_service = i18n_service

    # Community translations (Phase 18): the suggestion review queue
    # publishes approved values into i18n_translations through the i18n
    # repository, so it needs both ports wired from the same database.
    if translation_suggestion_service is None and settings.database_url:
        translation_suggestion_service = TranslationSuggestionService(
            PostgresTranslationSuggestionRepository(settings.database_url),
            PostgresI18nRepository(settings.database_url),
        )
    app.state.translation_suggestion_service = translation_suggestion_service

    # add_middleware prepends: the LAST registration is the OUTERMOST layer.
    # Order: RateLimit innermost (so 429s pass through CORS and carry CORS
    # headers), CORS, then RequestId outermost so even rate-limited and
    # preflight responses carry X-REQUEST-ID.
    rate_limiter = rate_limiter or build_rate_limiter(settings, redis_client)
    app.state.rate_limiter = rate_limiter
    app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)
    # Unversioned system probes: orchestrators (Cloud Run) must be able to
    # check liveness/readiness without API versioning.
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


def main() -> None:
    """Run the development server (console script ``annex-api``)."""
    import os

    import uvicorn

    settings = get_settings()
    # PaaS platforms (Cloud Run, Render, Heroku) inject PORT and require
    # the process to listen on it; 8000 remains the local default.
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )


# Module-level instance for ASGI servers (uvicorn app.main:app). Built once
# at import time; tests construct isolated instances via create_app().
app = create_app()


if __name__ == "__main__":
    main()
