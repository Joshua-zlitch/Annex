"""Core domain layer.

This package contains the innermost layer of the application: framework-free
business entities, domain errors and ports (interfaces). Nothing in this layer
may import from FastAPI, Supabase, OpenAI or any other external package.
"""

from app.core import entities, exceptions

__all__ = ["entities", "exceptions"]
