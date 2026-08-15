from __future__ import annotations

import pytest

from app.core.entities.analysis import AnalysisStatus
from app.core.entities.media import MediaType
from app.core.exceptions import UnsupportedMediaTypeError, ValidationError
from app.core.use_cases.ingest_media import SubmitMediaInput, SubmitMediaUseCase
from tests.unit.fakes import FakeAnalysisRepository, FakeMediaRepository


@pytest.fixture
def usecase():
    return SubmitMediaUseCase(FakeMediaRepository(), FakeAnalysisRepository())


async def test_text_media_creates_media_and_pending_analysis(usecase):
    media, analysis = await usecase.execute(
        SubmitMediaInput(owner_id="user-1", media_type="text", source="text", text_content="hello")
    )

    assert media.owner_id == "user-1"
    assert media.media_type is MediaType.TEXT
    assert media.text_content == "hello"
    assert analysis.media_id == media.id
    assert analysis.owner_id == "user-1"
    assert analysis.status is AnalysisStatus.PENDING


async def test_image_media_requires_storage_path(usecase):
    with pytest.raises(ValidationError):
        await usecase.execute(
            SubmitMediaInput(owner_id="user-1", media_type="image", source="upload")
        )


async def test_blank_text_is_rejected(usecase):
    with pytest.raises(ValidationError):
        await usecase.execute(
            SubmitMediaInput(owner_id="user-1", media_type="text", source="text", text_content="  ")
        )


async def test_unsupported_media_type_is_rejected(usecase):
    with pytest.raises(UnsupportedMediaTypeError):
        await usecase.execute(
            SubmitMediaInput(owner_id="user-1", media_type="video", source="upload")
        )