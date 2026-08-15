from __future__ import annotations

import asyncio

from app.core.entities.user import User
from app.core.exceptions import AuthenticationError, ExternalServiceError
from app.core.ports.auth import AuthProvider
from app.infrastructure.config import Settings
from supabase import Client, create_client


class SupabaseAuthProvider(AuthProvider):
    """Validates JWTs against Supabase Auth using the anon (public) key."""

    def __init__(self, settings: Settings):
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise ExternalServiceError("Supabase credentials are not configured")
        self._client: Client = create_client(settings.supabase_url, settings.supabase_anon_key)

    async def get_user(self, token: str) -> User:
        try:
            response = await asyncio.to_thread(lambda: self._client.auth.get_user(token))
        except Exception as exc:  # noqa: BLE001 - invalid tokens raise AuthApiError
            raise AuthenticationError("invalid or expired token") from exc
        if response.user is None:
            raise AuthenticationError("invalid or expired token")
        return User(id=response.user.id, email=response.user.email)
