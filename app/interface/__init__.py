"""Interface layer: delivery mechanisms (FastAPI) that translate HTTP
requests into use case calls and domain errors into HTTP responses."""

from app.interface import api, dependencies

__all__ = ["api", "dependencies"]
