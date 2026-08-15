from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisResult:
    """Structured output produced by the AI analyst."""

    summary: str
    claims: list[str]
    credibility_score: float
    confidence: float
    reasoning: str
    flagged: bool = False


class AIProvider(ABC):
    """AI capabilities used by the platform (OpenAI in Phase 1)."""

    @abstractmethod
    async def extract_text_from_image(self, image_bytes: bytes, mime_type: str) -> str:
        """OCR a single image and return its verbatim text transcription."""

    @abstractmethod
    async def analyze_content(self, content: str) -> AnalysisResult:
        """Analyse transcribed content and produce a structured assessment."""
