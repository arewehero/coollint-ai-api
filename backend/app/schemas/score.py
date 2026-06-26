from typing import Optional

from pydantic import BaseModel, Field


class ScoresSchema(BaseModel):
    morning_score: int = Field(default=0, ge=0, le=10)
    daytime_score: int = Field(default=0, ge=0, le=10)
    night_score: int = Field(default=0, ge=0, le=10)
    irregular_score: int = Field(default=0, ge=0, le=10)
    stay_home_score: int = Field(default=0, ge=0, le=10)
    outing_score: int = Field(default=0, ge=0, le=10)
    cooling_need_score: int = Field(default=0, ge=0, le=10)
    saving_priority_score: int = Field(default=0, ge=0, le=10)
    saving_opportunity_score: int = Field(default=0, ge=0, le=10)
    heat_gain_score: int = Field(default=0, ge=0, le=10)
    cooling_loss_score: int = Field(default=0, ge=0, le=10)
    ventilation_score: int = Field(default=0, ge=0, le=10)


class ScoreCalculationRequest(BaseModel):
    date: Optional[str] = None
    weather_snapshot_id: str | None = None


class ScoreCalculationResponse(BaseModel):
    score_snapshot_id: str
    scores: ScoresSchema
    dominant_signals: list[str]


class ScoreSnapshotResponse(BaseModel):
    score_snapshot_id: str
    date: str
    morning_score: int = Field(ge=0, le=10)
    daytime_score: int = Field(ge=0, le=10)
    night_score: int = Field(ge=0, le=10)
    irregular_score: int = Field(ge=0, le=10)
    stay_home_score: int = Field(ge=0, le=10)
    outing_score: int = Field(ge=0, le=10)
    cooling_need_score: int = Field(ge=0, le=10)
    saving_priority_score: int = Field(ge=0, le=10)
    saving_opportunity_score: int = Field(ge=0, le=10)
    heat_gain_score: int = Field(ge=0, le=10)
    cooling_loss_score: int = Field(ge=0, le=10)
    ventilation_score: int = Field(ge=0, le=10)
    dominant_signals: list[str]
