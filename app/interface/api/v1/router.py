from fastapi import APIRouter

from app.interface.api.v1.routes import analysis, health, media

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(media.router)
api_router.include_router(analysis.router)
