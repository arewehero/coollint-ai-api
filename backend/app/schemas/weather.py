from pydantic import BaseModel


class WeatherTimeBlockSchema(BaseModel):
    time_range: str
    temperature: float
    feels_like: float | None = None
    humidity: int | None = None
    rain: bool = False
    uv_index: float | None = None
    heat_alert: bool = False
    weather_risk_score: int = 0


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
    time_blocks: list[WeatherTimeBlockSchema]


class WeatherRefreshRequest(BaseModel):
    date: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    region_name: str | None = None
