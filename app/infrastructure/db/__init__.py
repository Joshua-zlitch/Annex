"""Database adapters (Supabase PostgREST)."""

from app.infrastructure.db.supabase_repositories import (
    SupabaseAnalysisRepository,
    SupabaseMediaRepository,
)

__all__ = ["SupabaseAnalysisRepository", "SupabaseMediaRepository"]
