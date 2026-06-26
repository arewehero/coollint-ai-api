"""Analysis schemas for lifestyle analysis responses.

Requirements: 5.1, 5.2, 5.3
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LifestyleAnalysisResponse(BaseModel):
    analysis_id: UUID = Field(validation_alias="id", serialization_alias="analysis_id")
    primary_type: str
    secondary_type: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1, max_length=200)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
