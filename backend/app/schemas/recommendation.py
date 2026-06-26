from pydantic import BaseModel


class RecommendationActionSchema(BaseModel):
    action_id: str
    time_range: str
    sort_order: int
    action_type: str
    title: str
    action: str
    reason: str
    estimated_saving_krw: int
    estimated_energy_saving_kwh: float
    estimated_co2_reduction_kg: float
    difficulty: str
    is_completed: bool = False


class LifestyleAnalysisSummary(BaseModel):
    primary_type: str
    secondary_type: str | None = None
    confidence: float
    summary: str


class DailySummary(BaseModel):
    total_estimated_saving_krw: int
    monthly_estimated_saving_krw: int
    total_energy_saving_kwh: float
    total_co2_reduction_kg: float
    cheer_message: str | None = None


class DailyPlanResponse(BaseModel):
    plan_id: str
    date: str
    lifestyle_analysis: LifestyleAnalysisSummary
    daily_summary: DailySummary
    actions: list[RecommendationActionSchema]
    status: str


class DailyPlanRequest(BaseModel):
    date: str | None = None
    location: dict | None = None
    force_regenerate: bool = False


class ActionCompleteRequest(BaseModel):
    is_completed: bool


class TodayProgress(BaseModel):
    completed_action_count: int
    total_action_count: int
    completed_saving_krw: int
    today_estimated_saving_krw: int
    goal_achievement_rate: float
    message: str


class ActionCompleteResponse(BaseModel):
    action_id: str
    is_completed: bool
    completed_at: str | None = None
    delta: dict
    today_progress: TodayProgress
