from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str
    position: int


class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    credibility_score: float
    confidence: float
    flagged: bool
    reasoning: str


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    media_id: str
    owner_id: str
    status: str
    ocr_text: str | None = None
    summary: str | None = None
    claims: list[ClaimOut] = []
    assessment: AssessmentOut | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class AnalysisListOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AnalysisOut]
