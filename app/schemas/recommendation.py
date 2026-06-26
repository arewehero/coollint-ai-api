from __future__ import annotations

import datetime as dt
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DailyPlanLocationRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    region_name: Optional[str] = None


class GenerateDailyPlanRequest(BaseModel):
    date: Optional[dt.date] = None
    location: Optional[DailyPlanLocationRequest] = None
    force_regenerate: bool = False


class LifestyleAnalysisResponse(BaseModel):
    primary_type: str
    secondary_type: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    summary: str

    model_config = ConfigDict(from_attributes=True)


class DailySummaryResponse(BaseModel):
    total_estimated_saving_krw: int
    monthly_estimated_saving_krw: int
    total_energy_saving_kwh: float
    total_co2_reduction_kg: float
    cheer_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationActionResponse(BaseModel):
    action_id: UUID = Field(validation_alias="id", serialization_alias="action_id")
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
    is_completed: bool

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DailyPlanResponse(BaseModel):
    plan_id: UUID = Field(validation_alias="id", serialization_alias="plan_id")
    date: dt.date
    lifestyle_analysis: Optional[LifestyleAnalysisResponse] = None
    daily_summary: DailySummaryResponse
    actions: List[RecommendationActionResponse]
    status: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ToggleActionRequest(BaseModel):
    is_completed: bool


class ToggleActionDeltaResponse(BaseModel):
    saving_krw: int
    energy_saving_kwh: float
    co2_reduction_kg: float


class TodayProgressResponse(BaseModel):
    completed_action_count: int
    total_action_count: int
    completed_saving_krw: int
    today_estimated_saving_krw: int
    goal_achievement_rate: float
    message: str


class ToggleActionResponse(BaseModel):
    action_id: UUID
    is_completed: bool
    completed_at: Optional[dt.datetime] = None
    delta: ToggleActionDeltaResponse
    today_progress: TodayProgressResponse


class SavingsGoalResponse(BaseModel):
    monthly_electricity_bill: int
    monthly_goal_bill: Optional[int] = None
    required_monthly_saving_krw: Optional[int] = None
    current_projected_saving_krw: int
    on_track: bool


class SavingsSummaryResponse(BaseModel):
    period: Literal["today", "week", "month"] = Field(validation_alias="period_type", serialization_alias="period")
    period_start: dt.date
    period_end: dt.date
    completed_action_count: int
    total_action_count: int
    total_saving_krw: int
    total_possible_saving_krw: int
    total_energy_saving_kwh: float
    total_possible_energy_saving_kwh: float
    total_co2_reduction_kg: float
    total_possible_co2_reduction_kg: float
    monthly_projected_saving_krw: Optional[int] = None
    goal: Optional[SavingsGoalResponse] = None
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SavingsCalendarDayResponse(BaseModel):
    date: dt.date
    completed_action_count: int
    total_saving_krw: int
    total_co2_reduction_kg: float


class SavingsCalendarMonthlyTotalResponse(BaseModel):
    saving_krw: int
    energy_saving_kwh: float
    co2_reduction_kg: float


class SavingsCalendarResponse(BaseModel):
    month: str
    days: List[SavingsCalendarDayResponse]
    monthly_total: SavingsCalendarMonthlyTotalResponse
