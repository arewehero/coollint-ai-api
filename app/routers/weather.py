"""Weather router — hourly weather data endpoint.

GET /api/v1/weather/hourly returns time-block grouped weather data.
Does NOT require authentication (user can request weather without auth).

Fallback chain: cache → expired cache → 503 Service Unavailable
Requirements: 3.1, 3.6, 3.7
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.errors import ApiException, ErrorCode, api_meta_from_request
from app.db.session import get_db
from app.schemas.common import ApiSuccessResponse
from app.schemas.weather import WeatherHourlyResponse
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


def get_weather_service() -> WeatherService:
    return WeatherService()


@router.get(
    "/hourly",
    response_model=ApiSuccessResponse[WeatherHourlyResponse],
    summary="시간별 날씨 조회",
    description="Time_Range 6개 블록으로 그룹화된 시간별 날씨 정보를 반환합니다. "
    "위치 정보가 없으면 서울 기본 좌표(37.5665, 126.9780)를 사용합니다.",
)
def get_hourly_weather(
    request: Request,
    latitude: Optional[float] = Query(None, description="위도 (기본값: 서울 37.5665)"),
    longitude: Optional[float] = Query(None, description="경도 (기본값: 서울 126.9780)"),
    date: Optional[str] = Query(None, description="조회 날짜 (ISO 8601: YYYY-MM-DD, 기본값: 오늘)"),
    db: Session = Depends(get_db),
    weather_service: WeatherService = Depends(get_weather_service),
) -> ApiSuccessResponse[WeatherHourlyResponse]:
    """Get hourly weather data grouped by 6 Time_Range blocks.

    Fallback chain (Req 3.6):
    1. Valid cache (expires_at > now) → return cached data
    2. Provider fails → expired cache → return stale data
    3. No cache at all → 503 Service Unavailable
    """
    # Parse optional date parameter (Req 11.3)
    target_date: Optional[dt.date] = None
    if date is not None:
        try:
            target_date = dt.date.fromisoformat(date)
        except (ValueError, TypeError):
            raise ApiException.from_error_code(
                ErrorCode.INVALID_DATE_FORMAT,
                message="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요.",
            )

    # WeatherService handles cache logic, provider call, and fallback (Req 3.1, 3.6, 3.7)
    weather_response = weather_service.get_hourly_weather(
        db,
        date=target_date,
        lat=latitude,
        lon=longitude,
    )

    return ApiSuccessResponse(
        data=weather_response,
        meta=api_meta_from_request(request),
    )
