from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from app.core.entities.analysis import Analysis, AnalysisStatus, Assessment, Claim
from app.core.entities.media import Media, MediaSource, MediaType
from app.core.exceptions import ExternalServiceError
from app.core.ports.repositories import (
    AnalysisRepository,
    AnalysisUpdate,
    MediaRepository,
)
from app.infrastructure.config import Settings
from supabase import Client, create_client

_MEDIA_COLUMNS = (
    "id, owner_id, media_type, source, storage_path, source_url, text_content, "
    "filename, mime_type, created_at"
)
_ANALYSIS_COLUMNS = (
    "id, media_id, owner_id, status, ocr_text, summary, credibility_score, "
    "confidence, flagged, reasoning, error, created_at, completed_at"
)


def _build_client(settings: Settings) -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ExternalServiceError("Supabase credentials are not configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _media_from_row(row: dict) -> Media:
    return Media(
        id=row["id"],
        owner_id=row["owner_id"],
        media_type=MediaType(row["media_type"]),
        source=MediaSource(row["source"]),
        storage_path=row.get("storage_path"),
        source_url=row.get("source_url"),
        text_content=row.get("text_content"),
        filename=row.get("filename"),
        mime_type=row.get("mime_type"),
        created_at=_parse_datetime(row.get("created_at")),
    )


def _analysis_from_row(row: dict, claims: list[dict] | None = None) -> Analysis:
    assessment = None
    if row.get("credibility_score") is not None:
        assessment = Assessment(
            credibility_score=float(row["credibility_score"]),
            confidence=float(row.get("confidence") or 0.0),
            flagged=bool(row.get("flagged") or False),
            reasoning=row.get("reasoning") or "",
        )
    claim_objects = [
        Claim(
            id=claim["id"],
            analysis_id=claim["analysis_id"],
            owner_id=claim["owner_id"],
            text=claim["text"],
            position=int(claim.get("position") or 0),
            created_at=_parse_datetime(claim.get("created_at")),
        )
        for claim in (claims or [])
    ]
    return Analysis(
        id=row["id"],
        media_id=row["media_id"],
        owner_id=row["owner_id"],
        status=AnalysisStatus(row.get("status") or AnalysisStatus.PENDING.value),
        ocr_text=row.get("ocr_text"),
        summary=row.get("summary"),
        claims=claim_objects,
        assessment=assessment,
        error=row.get("error"),
        created_at=_parse_datetime(row.get("created_at")),
        completed_at=_parse_datetime(row.get("completed_at")),
    )


def _parse_datetime(value: str | None) -> Any | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class SupabaseMediaRepository(MediaRepository):
    def __init__(self, settings: Settings):
        self._client = _build_client(settings)

    async def create(self, media: Media) -> Media:
        row = {
            "id": media.id,
            "owner_id": media.owner_id,
            "media_type": media.media_type.value,
            "source": media.source.value,
            "storage_path": media.storage_path,
            "source_url": media.source_url,
            "text_content": media.text_content,
            "filename": media.filename,
            "mime_type": media.mime_type,
        }
        result = await asyncio.to_thread(
            lambda: self._client.table("media").insert(row).select(_MEDIA_COLUMNS).execute()
        )
        return _media_from_row(result.data[0])

    async def get(self, media_id: str) -> Media | None:
        result = await asyncio.to_thread(
            lambda: (
                self._client.table("media")
                .select(_MEDIA_COLUMNS)
                .eq("id", media_id)
                .maybe_single()
                .execute()
            )
        )
        return _media_from_row(result.data) if result.data else None

    async def list_by_owner(self, owner_id: str) -> list[Media]:
        result = await asyncio.to_thread(
            lambda: (
                self._client.table("media")
                .select(_MEDIA_COLUMNS)
                .eq("owner_id", owner_id)
                .order("created_at", desc=True)
                .execute()
            )
        )
        return [_media_from_row(row) for row in result.data]


class SupabaseAnalysisRepository(AnalysisRepository):
    def __init__(self, settings: Settings):
        self._client = _build_client(settings)

    async def create(self, analysis: Analysis) -> Analysis:
        row = {"id": analysis.id, "media_id": analysis.media_id, "owner_id": analysis.owner_id}
        result = await asyncio.to_thread(
            lambda: self._client.table("analysis").insert(row).select(_ANALYSIS_COLUMNS).execute()
        )
        return _analysis_from_row(result.data[0])

    async def get(self, analysis_id: str) -> Analysis | None:
        result = await asyncio.to_thread(
            lambda: (
                self._client.table("analysis")
                .select(_ANALYSIS_COLUMNS)
                .eq("id", analysis_id)
                .maybe_single()
                .execute()
            )
        )
        if not result.data:
            return None
        claims = await self._fetch_claims(analysis_id)
        return _analysis_from_row(result.data, claims)

    async def list_by_media(self, media_id: str) -> list[Analysis]:
        result = await asyncio.to_thread(
            lambda: (
                self._client.table("analysis")
                .select(_ANALYSIS_COLUMNS)
                .eq("media_id", media_id)
                .order("created_at", desc=True)
                .execute()
            )
        )
        analyses: list[Analysis] = []
        for row in result.data:
            claims = await self._fetch_claims(row["id"])
            analyses.append(_analysis_from_row(row, claims))
        return analyses

    async def update(self, analysis_id: str, update: AnalysisUpdate) -> None:
        patch: dict = {"status": update.status}
        if update.ocr_text is not None:
            patch["ocr_text"] = update.ocr_text
        if update.summary is not None:
            patch["summary"] = update.summary
        if update.credibility_score is not None:
            patch["credibility_score"] = update.credibility_score
        if update.confidence is not None:
            patch["confidence"] = update.confidence
        if update.flagged is not None:
            patch["flagged"] = update.flagged
        if update.reasoning is not None:
            patch["reasoning"] = update.reasoning
        if update.error is not None:
            patch["error"] = update.error
        if update.completed_at is not None:
            patch["completed_at"] = update.completed_at

        await asyncio.to_thread(
            lambda: self._client.table("analysis").update(patch).eq("id", analysis_id).execute()
        )

        if update.claims is not None:
            await self._replace_claims(analysis_id, update.claims)

    async def _fetch_claims(self, analysis_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: (
                self._client.table("claims")
                .select("id, analysis_id, owner_id, text, position, created_at")
                .eq("analysis_id", analysis_id)
                .order("position")
                .execute()
            )
        )
        return result.data

    async def _replace_claims(self, analysis_id: str, claims: list[dict]) -> None:
        owner = await asyncio.to_thread(
            lambda: (
                self._client.table("analysis")
                .select("owner_id")
                .eq("id", analysis_id)
                .maybe_single()
                .execute()
            )
        )
        owner_id = owner.data["owner_id"] if owner.data else None
        await asyncio.to_thread(
            lambda: self._client.table("claims").delete().eq("analysis_id", analysis_id).execute()
        )
        if not claims:
            return
        rows = [
            {
                "analysis_id": analysis_id,
                "owner_id": owner_id,
                "text": claim["text"],
                "position": claim["position"],
            }
            for claim in claims
        ]
        await asyncio.to_thread(lambda: self._client.table("claims").insert(rows).execute())
