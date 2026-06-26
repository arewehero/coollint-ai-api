from pydantic import BaseModel


class ScoresSchema(BaseModel):
    morning_score: int = 0
    daytime_score: int = 0
    night_score: int = 0
    irregular_score: int = 0
    stay_home_score: int = 0
    outing_score: int = 0
    cooling_need_score: int = 0
    saving_priority_score: int = 0
    saving_opportunity_score: int = 0
    heat_gain_score: int = 0
    cooling_loss_score: int = 0
    ventilation_score: int = 0


class ScoreCalculationRequest(BaseModel):
    date: str
    weather_snapshot_id: str | None = None


class ScoreCalculationResponse(BaseModel):
    score_snapshot_id: str
    scores: ScoresSchema
    dominant_signals: list[str]
