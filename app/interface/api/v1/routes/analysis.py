from fastapi import APIRouter, Depends

from app.core.entities.user import User
from app.infrastructure.container import Container
from app.interface.api.v1.schemas.analysis import AnalysisListOut, AnalysisOut
from app.interface.dependencies import get_container, get_current_user

router = APIRouter(tags=["analysis"])


@router.get("/analysis/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    analysis_id: str,
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
) -> AnalysisOut:
    analysis = await container.analysis_query_use_case.get_own(user.id, analysis_id)
    return AnalysisOut.model_validate(analysis)


@router.get("/media/{media_id}/analysis", response_model=AnalysisListOut)
async def list_media_analyses(
    media_id: str,
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
) -> AnalysisListOut:
    analyses = await container.analysis_query_use_case.list_for_media(user.id, media_id)
    return AnalysisListOut(items=[AnalysisOut.model_validate(a) for a in analyses])
