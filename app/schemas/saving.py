"""Saving summary schemas.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

from __future__ import annotations

import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SavingGoalInfo(BaseModel):
    monthly_goal_bill: int
    required_monthly_saving_krw: int
    current_projected_saving_krw: int
    on_track: bool


class SavingSummaryResponse(BaseModel):
    period: Literal["today", "week", "month"]
    period_start: dt.date
    period_end: dt.date
    completed_action_count: int = 0
    total_action_count: int = 0
    total_saving_krw: int = 0
    total_possible_saving_krw: int = 0
    total_energy_saving_kwh: float = 0.0
    total_co2_reduction_kg: float = 0.0
    monthly_projected_saving_krw: Optional[int] = None
    goal: Optional[SavingGoalInfo] = None
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
