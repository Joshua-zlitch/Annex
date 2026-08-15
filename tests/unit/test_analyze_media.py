from __future__ import annotations

import pytest

from app.core.entities.analysis import AnalysisStatus
from app.core.exceptions import NotFoundError
from app.core.use_cases.analyze_media import AnalyzeMediaUseCase
from app.core.use_cases.ingest_media import SubmitMediaInput, SubmitMediaUseCase
from tests.unit.fakes import FakeAIProvider


class BoomProvider(FakeAIProvider):
    async def analyze_content(self, content):
        raise RuntimeError("provider exploded")


@pytest.fixture
def fakes():
    from tests.unit.fakes import (
        FakeAnalysisRepository,
        FakeMediaRepository,
        FakeStorageProvider,
    )

    return {
        "media_repo": FakeMediaRepository(),
        "analysis_repo": FakeAnalysisRepository(),
        "ai_provider": FakeAIProvider(),
        "storage": FakeStorageProvider(),
    }


def build_usecase(fakes, ai_provider=None):
    return AnalyzeMediaUseCase(
        fakes["media_repo"],
        fakes["analysis_repo"],
        ai_provider or fakes["ai_provider"],
        fakes["storage"],
    )


async def submit(fakes, *, media_type="text", source="text", **kwargs):
    usecase = SubmitMediaUseCase(fakes["media_repo"], fakes["analysis_repo"])
    return await usecase.execute(SubmitMediaInput(owner_id="user-1", media_type=media_type, source=source, **kwargs))


async def test_analyze_text_media_completes(fakes):
    media, analysis = await submit(fakes, text_content="Some text to analyse")

    await build_usecase(fakes).execute(analysis.id)

    result = await fakes["analysis_repo"].get(analysis.id)
    assert result.status is AnalysisStatus.COMPLETED
    assert result.ocr_text == "Some text to analyse"
    assert result.summary == "A fake summary."
    assert [c.text for c in result.claims] == ["Claim one.", "Claim two."]
    assert result.assessment is not None
    assert result.assessment.credibility_score == 0.7
    assert fakes["ai_provider"].ocr_calls == 0
    assert fakes["ai_provider"].analyze_calls == 1


async def test_analyze_image_media_runs_ocr(fakes):
    media, analysis = await submit(
        fakes,
        media_type="image",
        source="upload",
        storage_path="user-1/abc/photo.png",
        mime_type="image/png",
    )
    await fakes["storage"].upload("user-1/abc/photo.png", b"raw-png-bytes", "image/png")

    await build_usecase(fakes).execute(analysis.id)

    result = await fakes["analysis_repo"].get(analysis.id)
    assert result.status is AnalysisStatus.COMPLETED
    assert result.ocr_text == "FAKE OCR TRANSCRIPTION"
    assert fakes["ai_provider"].ocr_calls == 1
    assert fakes["ai_provider"].analyze_calls == 1


async def test_analyze_marks_failed_and_reraises(fakes):
    media, analysis = await submit(fakes, text_content="boom")

    with pytest.raises(RuntimeError):
        await build_usecase(fakes, ai_provider=BoomProvider()).execute(analysis.id)

    result = await fakes["analysis_repo"].get(analysis.id)
    assert result.status is AnalysisStatus.FAILED
    assert "provider exploded" in result.error


async def test_analyze_unknown_analysis_raises(fakes):
    with pytest.raises(NotFoundError):
        await build_usecase(fakes).execute("does-not-exist")