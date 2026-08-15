"""Ports: abstract interfaces that the core layer depends on.

Adapters in ``app.infrastructure`` implement these interfaces. The core layer
never references concrete adapters (dependency inversion).
"""

from app.core.ports import ai_provider, auth, jobs, repositories, storage

__all__ = ["ai_provider", "auth", "jobs", "repositories", "storage"]
