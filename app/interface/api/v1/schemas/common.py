from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str


class SubmitMediaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_id: str
    analysis_id: str
    media_type: str
    source: str
    status: str
    created_at: str
