from __future__ import annotations

import datetime as dt
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import ApiException, ErrorCode, api_meta_from_request
from app.dependencies import get_current_user_id, get_db, get_saving_summary_service
from app.schemas.common import ApiSuccessResponse
from app.schemas.recommendation import SavingsCalendarResponse, SavingsSummaryResponse
from app.services.saving_summary_service import SavingSummaryService


router = APIRouter(prefix="/savings", tags=["Savings"])

_VALID_PERIODS = {"today", "week", "month"}


@router.get("/summary", response_model=ApiSuccessResponse[SavingsSummaryResponse])
def get_savings_summary(
    request: Request,
    period: str = "today",
    date: Optional[dt.date] = None,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    service: SavingSummaryService = Depends(get_saving_summary_service),
) -> ApiSuccessResponse[SavingsSummaryResponse]:
    if period not in _VALID_PERIODS:
        raise ApiException.from_error_code(ErrorCode.INVALID_PERIOD)
    summary = service.get_summary(db, user_id=user_id, period=period, reference_date=date)
    return ApiSuccessResponse(data=summary, meta=api_meta_from_request(request, include_generated_at=True))


@router.get("/calendar", response_model=ApiSuccessResponse[SavingsCalendarResponse])
def get_savings_calendar(
    request: Request,
    month: str,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    service: SavingSummaryService = Depends(get_saving_summary_service),
) -> ApiSuccessResponse[SavingsCalendarResponse]:
    calendar = service.get_calendar(db, user_id=user_id, month=month)
    return ApiSuccessResponse(data=calendar, meta=api_meta_from_request(request, include_generated_at=True))
