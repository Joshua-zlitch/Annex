from fastapi import APIRouter

from app.interface.api.v1.routes import analysis, auth, health, media

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(media.router)
api_router.include_router(analysis.router)
