"""Infrastructure layer: concrete adapters for the core ports.

Each adapter depends only on its port interface plus configuration, and hides
the underlying SDK (Supabase / OpenAI) from the rest of the application.
"""

from app.infrastructure import ai, auth, config, container, db, jobs, storage

__all__ = ["ai", "auth", "config", "container", "db", "jobs", "storage"]
