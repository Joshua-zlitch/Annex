from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.core.entities.media import utcnow


class AnalysisStatus(StrEnum):
    """Lifecycle of a media analysis job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Claim:
    """A single assertoric statement extracted from the analysed content."""

    text: str
    position: int = 0


@dataclass(slots=True)
class Assessment:
    """Credibility assessment produced by the AI analyst."""

    credibility_score: float = 0.0
    confidence: float = 0.0
    flagged: bool = False
    reasoning: str = ""


@dataclass(slots=True)
class Analysis:
    """The analysis job and result for a given piece of media."""

    id: str
    media_id: str
    owner_id: str
    status: AnalysisStatus = AnalysisStatus.PENDING
    ocr_text: str | None = None
    summary: str | None = None
    claims: list[Claim] = field(default_factory=list)
    assessment: Assessment | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None
