from __future__ import annotations

from app.core.entities.media import Media
from app.core.exceptions import NotFoundError
from app.core.ports.repositories import MediaRepository


class MediaQueryUseCase:
    """Read-only queries over media, always scoped to the requesting owner."""

    def __init__(self, media_repository: MediaRepository):
        self._media_repository = media_repository

    async def get_own(self, owner_id: str, media_id: str) -> Media:
        media = await self._media_repository.get(media_id)
        if media is None or media.owner_id != owner_id:
            raise NotFoundError(f"media '{media_id}' not found")
        return media

    async def list_own(self, owner_id: str) -> list[Media]:
        return await self._media_repository.list_by_owner(owner_id)
