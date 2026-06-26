from typing import Literal

from pydantic import BaseModel, Field


class WeatherTimeBlockSchema(BaseModel):
    time_range: Literal["새벽", "아침", "오전", "오후", "저녁", "밤"]
    temperature: float = Field(..., description="기온 (°C, 소수점 1자리)")
    feels_like: float = Field(..., description="체감온도 (°C, 소수점 1자리)")
    humidity: int = Field(..., ge=0, le=100, description="습도 (0~100 정수 %)")
    rain: bool = Field(..., description="강수 여부")
    heat_alert: bool = Field(..., description="폭염 경보 (기온 ≥ 35°C)")


class WeatherCacheInfo(BaseModel):
    hit: bool
    fetched_at: str | None = None
    expires_at: str | None = None


class WeatherLocation(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    region_name: str | None = None


class WeatherHourlyResponse(BaseModel):
    date: str
    provider: str
    cache: WeatherCacheInfo
    location: WeatherLocation
    time_blocks: list[WeatherTimeBlockSchema] = Field(
        ..., min_length=6, max_length=6, description="6개 시간대 블록"
    )


class WeatherRefreshRequest(BaseModel):
    date: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    region_name: str | None = None
