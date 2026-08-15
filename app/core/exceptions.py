"""Domain-level errors.

These are raised by the core layer (entities / use cases) and translated into
HTTP responses by the interface layer.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors."""


class ValidationError(DomainError):
    """Input data is semantically invalid."""


class UnsupportedMediaTypeError(ValidationError):
    """The media type is not supported by the current phase."""


class NotFoundError(DomainError):
    """A requested resource does not exist or is not owned by the caller."""


class AuthenticationError(DomainError):
    """Credentials are missing, invalid or expired."""


class ExternalServiceError(DomainError):
    """A downstream dependency (Supabase, OpenAI, ...) failed."""
