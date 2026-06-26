from pydantic import BaseModel


class LifestyleAnalysisRequest(BaseModel):
    date: str
    score_snapshot_id: str | None = None


class LifestyleAnalysisResponse(BaseModel):
    analysis_id: str
    primary_type: str
    secondary_type: str | None = None
    confidence: float
    summary: str
    reason: str | None = None
