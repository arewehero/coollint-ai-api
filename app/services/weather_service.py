"""Weather service orchestrating cache, provider, and fallback logic.

Provides:
- get_hourly_weather(date, lat, lon, region, force_refresh) → WeatherHourlyResponse

Flow:
1. Check DB cache (WeatherSnapshot where date matches and expires_at > now)
2. If cache hit → return cached time_blocks
3. If cache miss → call WeatherProvider
4. If provider fails → check expired cache
5. If no expired cache → raise ApiException(WEATHER_UNAVAILABLE, 503)
6. Save new snapshot with expires_at = now + 1 hour

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
"""

from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.errors import ApiException, ErrorCode
from app.core.time import KST, now_kst
from app.core.time_utils import get_kst_today
from app.models.weather import WeatherSnapshot
from app.repositories.weather_repository import WeatherRepository
from app.schemas.weather import WeatherHourlyResponse, WeatherTimeBlockSchema
from app.services.weather_provider import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    WeatherProvider,
    WeatherProviderError,
)

logger = logging.getLogger(__name__)

# Cache TTL: 1 hour (Req 3.4)
CACHE_TTL_SECONDS = 3600


class WeatherService:
    """Orchestrates weather data retrieval with DB caching and fallback."""

    def __init__(
        self,
        weather_repository: Optional[WeatherRepository] = None,
        weather_provider: Optional[WeatherProvider] = None,
    ) -> None:
        self.repository = weather_repository or WeatherRepository()
        self.provider = weather_provider or WeatherProvider()

    def get_hourly_weather(
        self,
        db: Session,
        *,
        date: Optional[dt.date] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        region: Optional[str] = None,
        force_refresh: bool = False,
    ) -> WeatherHourlyResponse:
        """Get hourly weather data grouped by 6 Time_Range blocks.

        Args:
            db: Database session
            date: Target date (defaults to today KST)
            lat: Latitude (defaults to Seoul 37.5665, Req 3.7)
            lon: Longitude (defaults to Seoul 126.9780, Req 3.7)
            region: Region name for caching metadata
            force_refresh: Skip cache and fetch fresh data

        Returns:
            WeatherHourlyResponse with 6 time blocks

        Raises:
            ApiException(WEATHER_UNAVAILABLE, 503) if all fallbacks fail (Req 3.6)
        """
        # Apply defaults
        target_date = date or get_kst_today()
        latitude = Decimal(str(lat)) if lat is not None else DEFAULT_LATITUDE
        longitude = Decimal(str(lon)) if lon is not None else DEFAULT_LONGITUDE

        # Step 1: Check DB cache (Req 3.3)
        if not force_refresh:
            cached_snapshot = self.repository.get_cached_snapshot(
                db, target_date, latitude, longitude
            )
            if cached_snapshot is not None:
                logger.debug(f"Weather cache hit for {target_date} ({latitude}, {longitude})")
                return self._snapshot_to_response(cached_snapshot, cached=True)

        # Step 2: Call WeatherProvider (Req 3.8: 5s timeout)
        try:
            raw_response = self.provider.fetch_forecast(
                lat=float(latitude),
                lon=float(longitude),
            )

            # Parse into time blocks
            time_blocks_data = self.provider.parse_forecast_to_time_blocks(
                raw_response, target_date
            )

            # Step 3: Save with 1-hour TTL (Req 3.4)
            expires_at = now_kst() + dt.timedelta(seconds=CACHE_TTL_SECONDS)
            snapshot = self.repository.save_snapshot(
                db,
                date=target_date,
                latitude=latitude,
                longitude=longitude,
                region_name=region,
                expires_at=expires_at,
                raw_response=raw_response,
                time_blocks_data=time_blocks_data,
            )

            return self._snapshot_to_response(snapshot, cached=False)

        except WeatherProviderError as e:
            logger.warning(f"Weather provider failed: {e}. Attempting fallback...")

            # Step 4: Fallback to expired cache (Req 3.6)
            expired_snapshot = self.repository.get_expired_snapshot(
                db, target_date, latitude, longitude
            )
            if expired_snapshot is not None:
                logger.info("Using expired cache as fallback")
                return self._snapshot_to_response(expired_snapshot, cached=True)

            # Step 5: No fallback available → 503 (Req 3.6)
            raise ApiException.from_error_code(
                ErrorCode.WEATHER_UNAVAILABLE,
                message="날씨 데이터를 조회할 수 없습니다. 캐시 데이터도 존재하지 않습니다.",
            )

    def _snapshot_to_response(
        self, snapshot: WeatherSnapshot, cached: bool
    ) -> WeatherHourlyResponse:
        """Convert a WeatherSnapshot ORM object to the response schema."""
        time_blocks = [
            WeatherTimeBlockSchema(
                time_range=block.time_range,
                temperature=round(float(block.temperature), 1),
                feels_like=round(float(block.feels_like), 1),
                humidity=int(block.humidity),
                rain=block.rain,
                heat_alert=block.heat_alert,
            )
            for block in sorted(
                snapshot.time_blocks,
                key=lambda b: _time_range_sort_order(b.time_range),
            )
        ]

        return WeatherHourlyResponse(
            date=snapshot.date,
            time_blocks=time_blocks,
            cached=cached,
        )


def _time_range_sort_order(time_range: str) -> int:
    """Return sort order for time range labels."""
    order = {"새벽": 0, "아침": 1, "오전": 2, "오후": 3, "저녁": 4, "밤": 5}
    return order.get(time_range, 99)
