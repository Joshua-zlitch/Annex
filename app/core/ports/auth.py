from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.entities.user import User


class AuthProvider(ABC):
    """User authentication / verification (Supabase Auth in Phase 1)."""

    @abstractmethod
    async def get_user(self, token: str) -> User:
        """Resolve a bearer token to a ``User`` or raise ``AuthenticationError``."""
