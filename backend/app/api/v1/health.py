"""Service health endpoints.

``/health`` is an unauthenticated liveness probe; ``/health/ready`` reports
readiness of configured dependencies. Both live outside the versioned
prefix so orchestrators can probe them without API versioning.
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.deps import get_settings_dep
from app.core.checks import DependencyCheck
from app.core.config import Settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings_dep)) -> dict[str, Any]:
    """Liveness probe — 200 whenever the process is serving requests."""
    return {
        "data": {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "timestamp": time.time(),
        }
    }


@router.get("/health/ready")
def readiness(request: Request) -> JSONResponse:
    """Readiness probe — reports each configured dependency's status.

    Returns 200 when every registered check passes and 503 (degraded) as
    soon as one fails, with per-check detail for operators.
    """
    checks: list[DependencyCheck] = list(getattr(request.app.state, "checks", []))
    results = [check.check() for check in checks]
    healthy = all(result.ok for result in results)
    payload = {
        "data": {
            "status": "ok" if healthy else "degraded",
            "checks": [
                {"name": result.name, "ok": result.ok, "detail": result.detail}
                for result in results
            ],
            "timestamp": time.time(),
        }
    }
    return JSONResponse(status_code=200 if healthy else 503, content=payload)


@router.get("/health/live")
def liveness() -> dict[str, Any]:
    """Kubernetes liveness probe — minimal response."""
    return {"status": "alive", "timestamp": time.time()}
