from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


def utcnow() -> datetime:
    """Timezone-aware UTC now (domain default factory)."""
    return datetime.now(UTC)


class MediaType(StrEnum):
    """The kind of content a user submits for analysis."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    TEXT = "text"
    URL = "url"


class MediaSource(StrEnum):
    """How the media entered the platform."""

    UPLOAD = "upload"
    URL = "url"
    TEXT = "text"


@dataclass(slots=True)
class Media:
    """A piece of media (image, text, ...) submitted by a user."""

    id: str
    owner_id: str
    media_type: MediaType
    source: MediaSource
    storage_path: str | None = None
    source_url: str | None = None
    text_content: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    created_at: datetime = field(default_factory=utcnow)
