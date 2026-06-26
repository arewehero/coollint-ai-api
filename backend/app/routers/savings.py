from fastapi import APIRouter, Request, Depends, Query
from uuid import UUID

from app.schemas.common import SuccessResponse
from app.core.security import get_current_user_id

router = APIRouter()


@router.get("/summary", response_model=SuccessResponse)
async def get_savings_summary(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    period: str = Query("today"),
    date: str | None = Query(None),
):
    """오늘/주간/월간 절약 요약 조회."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"period": period, "total_saving_krw": 0, "completed_action_count": 0},
        meta={"request_id": request.state.request_id},
    )


@router.get("/calendar", response_model=SuccessResponse)
async def get_savings_calendar(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    month: str = Query(...),
):
    """월간 캘린더 요약."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"month": month, "days": [], "monthly_total": {"saving_krw": 0, "energy_saving_kwh": 0, "co2_reduction_kg": 0}},
        meta={"request_id": request.state.request_id},
    )
