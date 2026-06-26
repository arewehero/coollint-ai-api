from pydantic import BaseModel, Field


# --- Sub-models ---


class LifestyleAnalysisSummary(BaseModel):
    primary_type: str
    secondary_type: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str


class DailySummary(BaseModel):
    total_estimated_saving_krw: int = Field(..., ge=0)
    monthly_estimated_saving_krw: int = Field(..., ge=0)
    total_energy_saving_kwh: float = Field(..., ge=0.0)
    total_co2_reduction_kg: float = Field(..., ge=0.0)
    cheer_message: str


class CompletionDelta(BaseModel):
    saving_krw_delta: int
    energy_kwh_delta: float
    co2_kg_delta: float


class TodayProgress(BaseModel):
    completed_action_count: int = Field(..., ge=0)
    total_action_count: int = Field(..., ge=0)
    goal_achievement_rate: float = Field(..., ge=0.0, le=1.0)
    message: str


# --- Request schemas ---


class DailyPlanRequest(BaseModel):
    date: str | None = None
    force_regenerate: bool = False
    location: dict | None = None  # {"latitude": float, "longitude": float}


class ActionToggleRequest(BaseModel):
    is_completed: bool


# Alias for backward compatibility
ActionCompleteRequest = ActionToggleRequest


# --- Response schemas ---


class RecommendationActionResponse(BaseModel):
    action_id: str
    time_range: str
    sort_order: int
    action_type: str
    title: str
    action: str  # description text
    reason: str
    estimated_saving_krw: int = Field(..., ge=0)
    estimated_energy_saving_kwh: float
    estimated_co2_reduction_kg: float
    difficulty: str
    priority_score: float
    is_completed: bool = False
    completed_at: str | None = None


# Alias for backward compatibility
RecommendationActionSchema = RecommendationActionResponse


class DailyPlanResponse(BaseModel):
    plan_id: str
    date: str
    lifestyle_analysis: LifestyleAnalysisSummary
    daily_summary: DailySummary
    actions: list[RecommendationActionResponse]
    status: str


class ActionToggleResponse(BaseModel):
    action_id: str
    is_completed: bool
    completed_at: str | None = None
    delta: CompletionDelta
    today_progress: TodayProgress


# Alias for backward compatibility
ActionCompleteResponse = ActionToggleResponse
