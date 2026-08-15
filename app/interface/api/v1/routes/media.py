from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile

from app.core.entities.media import MediaSource, MediaType
from app.core.entities.user import User
from app.core.exceptions import ValidationError
from app.core.use_cases.ingest_media import SubmitMediaInput
from app.infrastructure.container import Container
from app.infrastructure.jobs.background_runner import FastAPIBackgroundRunner
from app.interface.api.v1.schemas.common import SubmitMediaResponse
from app.interface.api.v1.schemas.media import MediaListOut, MediaOut, TextMediaCreate
from app.interface.dependencies import get_container, get_current_user

router = APIRouter(prefix="/media", tags=["media"])

_IMAGE_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
}


@router.post("/upload", response_model=SubmitMediaResponse, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
) -> SubmitMediaResponse:
    content_type = file.content_type or "application/octet-stream"
    if content_type not in _IMAGE_CONTENT_TYPES:
        raise ValidationError(
            f"unsupported content type '{content_type}'; upload an image in Phase 1"
        )

    content = await file.read()
    max_bytes = container.settings.max_upload_size_bytes
    if len(content) > max_bytes:
        raise ValidationError(
            f"file exceeds the {container.settings.max_upload_size_mb} MB upload limit"
        )

    storage_path = f"{user.id}/{uuid4().hex}/{file.filename or 'upload'}"
    stored_path = await container.storage_provider.upload(storage_path, content, content_type)

    media, analysis = await container.submit_media_use_case.execute(
        SubmitMediaInput(
            owner_id=user.id,
            media_type=MediaType.IMAGE,
            source=MediaSource.UPLOAD,
            storage_path=stored_path,
            filename=file.filename,
            mime_type=content_type,
        )
    )

    FastAPIBackgroundRunner(background_tasks).run_in_background(
        container.analyze_media_use_case.execute(analysis.id)
    )

    return SubmitMediaResponse(
        media_id=media.id,
        analysis_id=analysis.id,
        media_type=media.media_type.value,
        source=media.source.value,
        status=analysis.status.value,
        created_at=analysis.created_at.isoformat(),
    )


@router.post("/from-text", response_model=SubmitMediaResponse, status_code=201)
async def create_text_media(
    payload: TextMediaCreate,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
) -> SubmitMediaResponse:
    media, analysis = await container.submit_media_use_case.execute(
        SubmitMediaInput(
            owner_id=user.id,
            media_type=MediaType.TEXT,
            source=MediaSource.TEXT,
            text_content=payload.text,
        )
    )

    FastAPIBackgroundRunner(background_tasks).run_in_background(
        container.analyze_media_use_case.execute(analysis.id)
    )

    return SubmitMediaResponse(
        media_id=media.id,
        analysis_id=analysis.id,
        media_type=media.media_type.value,
        source=media.source.value,
        status=analysis.status.value,
        created_at=analysis.created_at.isoformat(),
    )


@router.get("", response_model=MediaListOut)
async def list_media(
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
) -> MediaListOut:
    items = await container.media_query_use_case.list_own(user.id)
    return MediaListOut(items=[MediaOut.model_validate(item) for item in items])


@router.get("/{media_id}", response_model=MediaOut)
async def get_media(
    media_id: str,
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
) -> MediaOut:
    media = await container.media_query_use_case.get_own(user.id, media_id)
    return MediaOut.model_validate(media)
