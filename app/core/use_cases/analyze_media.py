from __future__ import annotations

from app.core.entities.analysis import AnalysisStatus
from app.core.entities.media import Media, MediaType, utcnow
from app.core.exceptions import NotFoundError, UnsupportedMediaTypeError, ValidationError
from app.core.ports.ai_provider import AIProvider
from app.core.ports.repositories import AnalysisRepository, AnalysisUpdate, MediaRepository
from app.core.ports.storage import StorageProvider


class AnalyzeMediaUseCase:
    """Run the analysis pipeline for a single analysis job.

    Pipeline: mark processing -> obtain source text (OCR for images) -> AI
    analysis -> persist result. Any failure transitions the job to ``failed``
    with a recorded error message.
    """

    def __init__(
        self,
        media_repository: MediaRepository,
        analysis_repository: AnalysisRepository,
        ai_provider: AIProvider,
        storage_provider: StorageProvider,
    ):
        self._media_repository = media_repository
        self._analysis_repository = analysis_repository
        self._ai_provider = ai_provider
        self._storage_provider = storage_provider

    async def execute(self, analysis_id: str) -> None:
        analysis = await self._analysis_repository.get(analysis_id)
        if analysis is None:
            raise NotFoundError(f"analysis '{analysis_id}' not found")

        await self._analysis_repository.update(
            analysis_id, AnalysisUpdate(status=AnalysisStatus.PROCESSING.value)
        )

        try:
            media = await self._media_repository.get(analysis.media_id)
            if media is None:
                raise NotFoundError(f"media '{analysis.media_id}' not found")

            source_text = await self._extract_source_text(media)
            result = await self._ai_provider.analyze_content(source_text)

            await self._analysis_repository.update(
                analysis_id,
                AnalysisUpdate(
                    status=AnalysisStatus.COMPLETED.value,
                    ocr_text=source_text,
                    summary=result.summary,
                    credibility_score=result.credibility_score,
                    confidence=result.confidence,
                    flagged=result.flagged,
                    reasoning=result.reasoning,
                    claims=[
                        {"text": text, "position": index}
                        for index, text in enumerate(result.claims)
                    ],
                    completed_at=utcnow().isoformat(),
                ),
            )
        except UnsupportedMediaTypeError as exc:
            # Unsupported media types are a known, expected outcome: record the
            # failure and let the pipeline finish without propagating.
            await self._analysis_repository.update(
                analysis_id, AnalysisUpdate(status=AnalysisStatus.FAILED.value, error=str(exc))
            )
        except Exception as exc:  # noqa: BLE001 - pipeline must never crash the request
            await self._analysis_repository.update(
                analysis_id, AnalysisUpdate(status=AnalysisStatus.FAILED.value, error=str(exc))
            )
            raise

    async def _extract_source_text(self, media: Media) -> str:
        if media.media_type is MediaType.TEXT:
            return media.text_content or ""

        if media.media_type is MediaType.IMAGE:
            if not media.storage_path:
                raise ValidationError("image media has no stored content")
            image_bytes = await self._storage_provider.download(media.storage_path)
            return await self._ai_provider.extract_text_from_image(
                image_bytes, media.mime_type or "image/png"
            )

        raise UnsupportedMediaTypeError(
            f"analysis of media type '{media.media_type.value}' is not supported yet"
        )
