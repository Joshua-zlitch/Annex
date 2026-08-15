"""In-memory fakes for the core ports (no external services)."""

from __future__ import annotations

from typing import Optional

from app.core.entities.analysis import Analysis, AnalysisStatus, Assessment, Claim
from app.core.entities.media import Media
from app.core.entities.user import User
from app.core.exceptions import AuthenticationError
from app.core.ports.ai_provider import AIProvider, AnalysisResult
from app.core.ports.auth import AuthProvider
from app.core.ports.repositories import (
    AnalysisRepository,
    AnalysisUpdate,
    MediaRepository,
)
from app.core.ports.storage import StorageProvider


class FakeMediaRepository(MediaRepository):
    def __init__(self) -> None:
        self._items: dict[str, Media] = {}

    async def create(self, media: Media) -> Media:
        self._items[media.id] = media
        return media

    async def get(self, media_id: str) -> Optional[Media]:
        return self._items.get(media_id)

    async def list_by_owner(self, owner_id: str) -> list[Media]:
        return [m for m in self._items.values() if m.owner_id == owner_id]


class FakeAnalysisRepository(AnalysisRepository):
    def __init__(self) -> None:
        self._items: dict[str, Analysis] = {}

    async def create(self, analysis: Analysis) -> Analysis:
        self._items[analysis.id] = analysis
        return analysis

    async def get(self, analysis_id: str) -> Optional[Analysis]:
        return self._items.get(analysis_id)

    async def list_by_media(self, media_id: str) -> list[Analysis]:
        return [a for a in self._items.values() if a.media_id == media_id]

    async def update(self, analysis_id: str, update: AnalysisUpdate) -> None:
        analysis = self._items.get(analysis_id)
        if analysis is None:
            return
        analysis.status = AnalysisStatus(update.status)
        if update.ocr_text is not None:
            analysis.ocr_text = update.ocr_text
        if update.summary is not None:
            analysis.summary = update.summary
        if update.error is not None:
            analysis.error = update.error
        if update.completed_at is not None:
            analysis.completed_at = None  # fake ignores timestamps
        if update.credibility_score is not None or update.confidence is not None:
            analysis.assessment = Assessment(
                credibility_score=update.credibility_score or 0.0,
                confidence=update.confidence or 0.0,
                flagged=bool(update.flagged),
                reasoning=update.reasoning or "",
            )
        if update.claims is not None:
            analysis.claims = [
                Claim(text=claim["text"], position=int(claim["position"])) for claim in update.claims
            ]


class FakeAIProvider(AIProvider):
    def __init__(self) -> None:
        self.ocr_calls = 0
        self.analyze_calls = 0

    async def extract_text_from_image(self, image_bytes: bytes, mime_type: str) -> str:
        self.ocr_calls += 1
        return "FAKE OCR TRANSCRIPTION"

    async def analyze_content(self, content: str) -> AnalysisResult:
        self.analyze_calls += 1
        return AnalysisResult(
            summary="A fake summary.",
            claims=["Claim one.", "Claim two."],
            credibility_score=0.7,
            confidence=0.8,
            reasoning="Based on the fake content.",
            flagged=False,
        )


class FakeStorageProvider(StorageProvider):
    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        self._blobs[path] = content
        return path

    async def download(self, path: str) -> bytes:
        return self._blobs.get(path, b"fake image bytes")


class FakeAuthProvider(AuthProvider):
    def __init__(self, user: User | None = None) -> None:
        self._user = user or User(id="user-1", email="user@example.com")

    async def get_user(self, token: str) -> User:
        if token != "test-token":
            raise AuthenticationError("invalid token")
        return self._user