from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.entities.analysis import Analysis
from app.core.entities.media import Media


class MediaRepository(ABC):
    """Persistence for ``Media`` aggregates."""

    @abstractmethod
    async def create(self, media: Media) -> Media:
        """Persist a new media record and return it."""

    @abstractmethod
    async def get(self, media_id: str) -> Media | None:
        """Fetch a media record by id, or ``None``."""

    @abstractmethod
    async def list_by_owner(self, owner_id: str) -> list[Media]:
        """List all media owned by a user, newest first."""


@dataclass(slots=True)
class AnalysisUpdate:
    """Snapshot of the fields written back by the analysis pipeline."""

    status: str
    ocr_text: str | None = None
    summary: str | None = None
    credibility_score: float | None = None
    confidence: float | None = None
    flagged: bool | None = None
    reasoning: str | None = None
    claims: list[dict] | None = None
    error: str | None = None
    completed_at: str | None = None


class AnalysisRepository(ABC):
    """Persistence for ``Analysis`` aggregates (including claims)."""

    @abstractmethod
    async def create(self, analysis: Analysis) -> Analysis:
        """Persist a new analysis job and return it."""

    @abstractmethod
    async def get(self, analysis_id: str) -> Analysis | None:
        """Fetch an analysis by id (including claims), or ``None``."""

    @abstractmethod
    async def list_by_media(self, media_id: str) -> list[Analysis]:
        """List all analyses for a media record, newest first."""

    @abstractmethod
    async def update(self, analysis_id: str, update: AnalysisUpdate) -> None:
        """Apply a partial update and replace the claims for the analysis."""
