from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LifestyleAnalysisRequest(BaseModel):
    date: Optional[dt.date] = None
    score_snapshot_id: Optional[UUID] = None
    profile: Dict[str, Any] = Field(default_factory=dict)
    scores: Dict[str, Any] = Field(default_factory=dict)
    weather: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class LifestyleAnalysisInput(BaseModel):
    user_id: Optional[str] = None
    date: Optional[dt.date] = None
    profile: Dict[str, Any] = Field(default_factory=dict)
    scores: Dict[str, Any] = Field(default_factory=dict)
    weather: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class LifestyleAnalysisAIResponse(BaseModel):
    primary_type: str = Field(min_length=1, max_length=30)
    secondary_type: Optional[str] = Field(default=None, max_length=30)
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class LifestyleAnalysisEndpointResponse(LifestyleAnalysisAIResponse):
    analysis_id: UUID


class CandidateActionInput(BaseModel):
    candidate_id: str = Field(min_length=1)
    time_range: Optional[str] = None
    action_type: str = "general"
    title: Optional[str] = None
    action: Optional[str] = None
    reason: Optional[str] = None
    difficulty: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    estimated_saving_krw: Optional[int] = None
    estimated_energy_saving_kwh: Optional[float] = None
    estimated_co2_reduction_kg: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class DailyPlanCopyInput(BaseModel):
    user_id: Optional[str] = None
    date: Optional[dt.date] = None
    lifestyle_analysis: Optional[LifestyleAnalysisAIResponse] = None
    candidate_actions: List[CandidateActionInput] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class DailyPlanActionCopyAIResponse(BaseModel):
    candidate_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class DailyPlanCopyAIResponse(BaseModel):
    cheer_message: str = Field(min_length=1)
    actions: List[DailyPlanActionCopyAIResponse]

    model_config = ConfigDict(extra="forbid")
