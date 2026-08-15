from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.container import Container
from app.interface.api.errors import register_exception_handlers
from app.interface.api.v1.router import api_router


def create_app(
    settings: Settings | None = None,
    container: Container | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    container = container or Container.build()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="ANNEX - 'Learn Before You Believe' media and information literacy API.",
        debug=settings.debug,
    )
    app.state.settings = settings
    app.state.container = container

    allow_credentials = "*" not in settings.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app
