"""Score schemas for score snapshot responses.

Requirements: 4.1, 4.2, 4.3
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScoreCalculationRequest(BaseModel):
    date: Optional[dt.date] = None


class ScoreSnapshotResponse(BaseModel):
    score_snapshot_id: UUID = Field(validation_alias="id", serialization_alias="score_snapshot_id")
    date: dt.date
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
    dominant_signals: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
