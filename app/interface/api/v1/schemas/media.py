from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    media_type: str
    source: str
    storage_path: str | None = None
    source_url: str | None = None
    text_content: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    created_at: datetime


class MediaListOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MediaOut]


class TextMediaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20000)
