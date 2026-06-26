from typing import Optional

from pydantic import BaseModel, Field


class LifestyleAnalysisRequest(BaseModel):
    date: Optional[str] = None
    score_snapshot_id: str | None = None


class LifestyleAnalysisResponse(BaseModel):
    analysis_id: str
    primary_type: str
    secondary_type: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=200)
    reason: str | None = None
