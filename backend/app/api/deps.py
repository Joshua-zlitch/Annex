"""Shared FastAPI dependencies.

Settings resolve from ``app.state`` (injected at the factory); the
authenticated caller resolves from the bearer token through the token
verifier + user service also bound to ``app.state`` (ADR-0005).
"""

from collections.abc import Callable
from typing import cast

from fastapi import Request

from app.api.errors import AppError
from app.application.ports.ai import ClaimAnalyzer
from app.application.ports.auth import TokenVerificationError, TokenVerifier
from app.application.services.analysis_service import AnalysisService
from app.application.services.claims_service import ClaimsService
from app.application.services.class_service import ClassService
from app.application.services.education_service import EducationService
from app.application.services.i18n_service import I18nService
from app.application.services.media_service import MediaService
from app.application.services.source_service import SourceService
from app.application.services.translation_suggestion_service import (
    TranslationSuggestionService,
)
from app.application.services.user_service import UserService
from app.core.config import Settings
from app.domain.user import User


def get_settings_dep(request: Request) -> Settings:
    """Provide the application-bound settings to request handlers."""
    # app.state is untyped at runtime; the factory guarantees a Settings.
    return cast(Settings, request.app.state.settings)


def _get_token_verifier(request: Request) -> TokenVerifier:
    """Return the bound token verifier, or 503 when auth is not configured."""
    verifier: TokenVerifier | None = getattr(request.app.state, "token_verifier", None)
    if verifier is None:
        raise AppError(
            "auth.not_configured",
            "Authentication is not configured on this server.",
            status_code=503,
        )
    return verifier


def get_analysis_service_dep(request: Request) -> AnalysisService:
    """Return the bound analysis service, or 503 when it is not configured."""
    service: AnalysisService | None = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise AppError(
            "analysis.not_configured",
            "Analysis processing is not configured on this server.",
            status_code=503,
        )
    return service


def get_i18n_service_dep(request: Request) -> I18nService:
    """Return the bound i18n service, or 503 when it is not configured."""
    service: I18nService | None = getattr(request.app.state, "i18n_service", None)
    if service is None:
        raise AppError(
            "i18n.not_configured",
            "Translation delivery is not configured on this server.",
            status_code=503,
        )
    return service


def get_claims_service_dep(request: Request) -> ClaimsService:
    """Return the bound claims service, or 503 when it is not configured."""
    service: ClaimsService | None = getattr(request.app.state, "claims_service", None)
    if service is None:
        raise AppError(
            "claims.not_configured",
            "Claims persistence is not configured on this server.",
            status_code=503,
        )
    return service


def get_source_service_dep(request: Request) -> SourceService:
    """Return the bound source service, or 503 when it is not configured."""
    service: SourceService | None = getattr(request.app.state, "source_service", None)
    if service is None:
        raise AppError(
            "sources.not_configured",
            "The source registry is not configured on this server.",
            status_code=503,
        )
    return service


def get_media_service_dep(request: Request) -> MediaService:
    """Return the bound media service, or 503 when it is not configured."""
    service: MediaService | None = getattr(request.app.state, "media_service", None)
    if service is None:
        raise AppError(
            "media.not_configured",
            "Media processing is not configured on this server.",
            status_code=503,
        )
    return service


def get_translation_suggestion_service_dep(request: Request) -> TranslationSuggestionService:
    """Return the bound suggestion service, or 503 when it is not configured."""
    service: TranslationSuggestionService | None = getattr(
        request.app.state, "translation_suggestion_service", None
    )
    if service is None:
        raise AppError(
            "i18n.suggestions_not_configured",
            "Community translations are not configured on this server.",
            status_code=503,
        )
    return service


def get_education_service_dep(request: Request) -> EducationService:
    """Return the bound education service, or 503 when it is not configured."""
    service: EducationService | None = getattr(request.app.state, "education_service", None)
    if service is None:
        raise AppError(
            "education.not_configured",
            "The curriculum is not configured on this server.",
            status_code=503,
        )
    return service


def get_class_service_dep(request: Request) -> ClassService:
    """Return the bound class service, or 503 when it is not configured."""
    service: ClassService | None = getattr(request.app.state, "class_service", None)
    if service is None:
        raise AppError(
            "classes.not_configured",
            "Educator tools are not configured on this server.",
            status_code=503,
        )
    return service


def get_claim_analyzer_dep(request: Request) -> ClaimAnalyzer:
    """Return the bound claim analyzer, or 503 when it is not configured."""
    analyzer: ClaimAnalyzer | None = getattr(request.app.state, "claim_analyzer", None)
    if analyzer is None:
        raise AppError(
            "analysis.not_configured",
            "Analysis processing is not configured on this server.",
            status_code=503,
        )
    return analyzer


def get_optional_user(request: Request) -> User | None:
    """Resolve the caller when a bearer token is supplied, else None.

    Anonymous access: a missing token means an unauthenticated caller. A
    supplied token that fails validation also results in None (the API
    answers 401 only when authentication is explicitly required, not for
    optional-dependent routes).

    Raises:
        AppError 503: authentication is not configured.
    """
    if not request.headers.get("Authorization"):
        return None
    try:
        return get_current_user(request)
    except AppError:
        return None


def get_current_user(request: Request) -> User:
    """Resolve the authenticated caller from the bearer token.

    Parses ``Authorization: Bearer <id-token>``, verifies the token through
    the bound verifier (ADR-0005), hydrates the user mirror, and attaches
    the user to ``request.state`` for downstream dependencies.

    Raises:
        AppError 401: missing or invalid token.
        AppError 503: authentication is not configured.
    """
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise AppError("auth.missing_token", "A bearer token is required.", status_code=401)
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AppError("auth.missing_token", "A bearer token is required.", status_code=401)

    verifier = _get_token_verifier(request)
    try:
        identity = verifier.verify(token)
    except TokenVerificationError:
        # Never reveal why verification failed (expired vs malformed ...).
        raise AppError(
            "auth.invalid_token", "The token is invalid or expired.", status_code=401
        ) from None

    user_service: UserService = cast(UserService, request.app.state.user_service)
    user = user_service.get_or_create(identity)
    request.state.current_user = user
    return user


def require_roles(*roles: str) -> Callable[[Request], User]:
    """Dependency factory: allow only callers holding one of the given roles.

    Usage: ``def admin_only(user: User = Depends(require_roles("admin"))): ...``

    Authorization is enforced at the service boundary, never only in the
    client UI (SECURITY.md / ADR-0003).

    Args:
        roles: Roles permitted to call the guarded endpoint.

    Returns:
        A FastAPI dependency resolving to the authorized caller.
    """

    def _role_dependency(request: Request) -> User:
        user = get_current_user(request)
        if user.role not in roles:
            raise AppError(
                "auth.insufficient_role",
                "Insufficient role for this operation.",
                status_code=403,
            )
        return user

    return _role_dependency
