from __future__ import annotations

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Blob storage for raw media (Supabase Storage in Phase 1).

    The provider is bound to a single media bucket, so paths are bucket-relative.
    """

    @abstractmethod
    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        """Store ``content`` at ``path`` and return the stored path."""

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Read and return the bytes stored at ``path``."""
