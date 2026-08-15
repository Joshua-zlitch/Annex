from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class User:
    """An authenticated user (mirrors a Supabase Auth user)."""

    id: str
    email: str | None = None
