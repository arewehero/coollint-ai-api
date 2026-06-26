from fastapi import APIRouter, Request, Depends, Query
from uuid import UUID

from app.schemas.common import SuccessResponse
from app.schemas.weather import WeatherRefreshRequest
from app.core.security import get_current_user_id

router = APIRouter()


@router.get("/hourly", response_model=SuccessResponse)
async def get_hourly_weather(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    date: str | None = Query(None),
    latitude: float | None = Query(None),
    longitude: float | None = Query(None),
    region_name: str | None = Query(None),
    force_refresh: bool = Query(False),
):
    """시간대별 날씨 조회."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"date": date, "provider": "openweathermap", "time_blocks": []},
        meta={"request_id": request.state.request_id},
    )


@router.post("/refresh", response_model=SuccessResponse)
async def refresh_weather(request: Request, body: WeatherRefreshRequest, user_id: UUID = Depends(get_current_user_id)):
    """날씨 수동 갱신."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"refreshed": True},
        meta={"request_id": request.state.request_id},
    )
