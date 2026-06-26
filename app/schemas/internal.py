from __future__ import annotations

import datetime as dt
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


InternalJobTarget = Literal["all_active_users"]


class GenerateDailyRecommendationsJobRequest(BaseModel):
    date: Optional[dt.date] = None
    target: InternalJobTarget = "all_active_users"
    dry_run: bool = False


class InternalJobErrorResponse(BaseModel):
    user_id: str
    error_code: str
    message: Optional[str] = None


class GenerateDailyRecommendationsJobResponse(BaseModel):
    date: dt.date
    target: InternalJobTarget
    total_users: int
    generated_count: int
    skipped_count: int
    failed_count: int
    errors: List[InternalJobErrorResponse] = Field(default_factory=list)
