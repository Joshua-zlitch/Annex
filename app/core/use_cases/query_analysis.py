from __future__ import annotations

from app.core.entities.analysis import Analysis
from app.core.exceptions import NotFoundError
from app.core.ports.repositories import AnalysisRepository


class AnalysisQueryUseCase:
    """Read-only queries over analyses, always scoped to the requesting owner."""

    def __init__(self, analysis_repository: AnalysisRepository):
        self._analysis_repository = analysis_repository

    async def get_own(self, owner_id: str, analysis_id: str) -> Analysis:
        analysis = await self._analysis_repository.get(analysis_id)
        if analysis is None or analysis.owner_id != owner_id:
            raise NotFoundError(f"analysis '{analysis_id}' not found")
        return analysis

    async def list_for_media(self, owner_id: str, media_id: str) -> list[Analysis]:
        analyses = await self._analysis_repository.list_by_media(media_id)
        return [a for a in analyses if a.owner_id == owner_id]
