from __future__ import annotations

import asyncio

from app.core.exceptions import ExternalServiceError
from app.core.ports.storage import StorageProvider
from app.infrastructure.config import Settings
from supabase import Client, create_client


class SupabaseStorageProvider(StorageProvider):
    """Supabase Storage adapter bound to the configured media bucket."""

    def __init__(self, settings: Settings):
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ExternalServiceError("Supabase credentials are not configured")
        self._client: Client = create_client(
            settings.supabase_url, settings.supabase_service_role_key
        )
        self._bucket = settings.supabase_media_bucket

    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        try:
            await asyncio.to_thread(
                lambda: self._client.storage.from_(self._bucket).upload(
                    path, content, {"content-type": content_type}
                )
            )
        except Exception as exc:  # noqa: BLE001 - SDK raises typed/unttyped errors
            raise ExternalServiceError(f"upload to storage failed: {exc}") from exc
        return path

    async def download(self, path: str) -> bytes:
        try:
            data = await asyncio.to_thread(
                lambda: self._client.storage.from_(self._bucket).download(path)
            )
        except Exception as exc:  # noqa: BLE001
            raise ExternalServiceError(f"download from storage failed: {exc}") from exc
        return data
