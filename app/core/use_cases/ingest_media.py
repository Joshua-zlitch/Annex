from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.core.entities.analysis import Analysis
from app.core.entities.media import Media, MediaSource, MediaType
from app.core.exceptions import UnsupportedMediaTypeError, ValidationError
from app.core.ports.repositories import AnalysisRepository, MediaRepository

# Media types fully supported by Phase 1.
_SUPPORTED_MEDIA_TYPES = frozenset({MediaType.IMAGE, MediaType.TEXT})


@dataclass(slots=True)
class SubmitMediaInput:
    """Validated input for the submit-media use case."""

    owner_id: str
    media_type: MediaType
    source: MediaSource
    storage_path: str | None = None
    source_url: str | None = None
    text_content: str | None = None
    filename: str | None = None
    mime_type: str | None = None

    def __post_init__(self) -> None:
        # Normalise plain-string inputs (e.g. from API schemas) to enum members.
        self.media_type = MediaType(self.media_type)
        self.source = MediaSource(self.source)


class SubmitMediaUseCase:
    """Persist a new piece of media and enqueue a pending analysis for it.

    The actual (expensive) analysis work is scheduled separately by the caller
    via ``AnalyzeMediaUseCase``.
    """

    def __init__(self, media_repository: MediaRepository, analysis_repository: AnalysisRepository):
        self._media_repository = media_repository
        self._analysis_repository = analysis_repository

    async def execute(self, input_: SubmitMediaInput) -> tuple[Media, Analysis]:
        self._validate(input_)

        media = Media(
            id=uuid4().hex,
            owner_id=input_.owner_id,
            media_type=input_.media_type,
            source=input_.source,
            storage_path=input_.storage_path,
            source_url=input_.source_url,
            text_content=input_.text_content,
            filename=input_.filename,
            mime_type=input_.mime_type,
        )
        media = await self._media_repository.create(media)

        analysis = Analysis(id=uuid4().hex, media_id=media.id, owner_id=media.owner_id)
        analysis = await self._analysis_repository.create(analysis)

        return media, analysis

    def _validate(self, input_: SubmitMediaInput) -> None:
        try:
            media_type = MediaType(input_.media_type)
        except ValueError:
            raise UnsupportedMediaTypeError(f"unknown media type '{input_.media_type}'") from None

        if media_type not in _SUPPORTED_MEDIA_TYPES:
            raise UnsupportedMediaTypeError(
                f"media type '{media_type.value}' is not supported yet "
                f"(supported: {sorted(t.value for t in _SUPPORTED_MEDIA_TYPES)})"
            )

        input_.media_type = media_type

        try:
            input_.source = MediaSource(input_.source)
        except ValueError:
            raise ValidationError(f"unknown media source '{input_.source}'") from None

        if media_type is MediaType.TEXT:
            if not input_.text_content or not input_.text_content.strip():
                raise ValidationError("'text_content' is required for text media")
        elif media_type is MediaType.IMAGE:
            if not input_.storage_path:
                raise ValidationError("'storage_path' is required for uploaded images")
