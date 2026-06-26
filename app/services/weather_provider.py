"""Weather provider for OpenWeatherMap 5-day/3-hour forecast API.

Provides:
- fetch_forecast(lat, lon) → list of hourly data points from OWM API

Requirements: 3.1, 3.7, 3.8
"""

from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.time import KST
from app.core.time_utils import TIME_RANGES, get_time_range

logger = logging.getLogger(__name__)

# Default coordinates: Seoul (Req 3.7)
DEFAULT_LATITUDE = Decimal("37.5665")
DEFAULT_LONGITUDE = Decimal("126.9780")

# httpx timeout: 5 seconds (Req 3.8)
WEATHER_API_TIMEOUT = 5.0

# OpenWeatherMap 5day/3h forecast endpoint
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


class WeatherProviderError(Exception):
    """Raised when the weather provider cannot fetch data."""

    pass


class WeatherProvider:
    """Fetches weather data from OpenWeatherMap 5-day/3-hour forecast API."""

    def fetch_forecast(
        self,
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        """Call OpenWeatherMap 5day/3h API and return raw response.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate

        Returns:
            Raw JSON response from OpenWeatherMap

        Raises:
            WeatherProviderError: If API call fails or times out (Req 3.8)
        """
        api_key = settings.openweathermap_api_key
        if not api_key:
            raise WeatherProviderError("OpenWeatherMap API key is not configured")

        params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric",
            "lang": "kr",
        }

        try:
            with httpx.Client(timeout=WEATHER_API_TIMEOUT) as client:
                response = client.get(OWM_FORECAST_URL, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            logger.warning(f"Weather API timeout for ({lat}, {lon}): {e}")
            raise WeatherProviderError(f"Weather API timeout: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.warning(f"Weather API HTTP error for ({lat}, {lon}): {e.response.status_code}")
            raise WeatherProviderError(f"Weather API HTTP error: {e.response.status_code}") from e
        except httpx.HTTPError as e:
            logger.warning(f"Weather API error for ({lat}, {lon}): {e}")
            raise WeatherProviderError(f"Weather API error: {e}") from e

    def parse_forecast_to_time_blocks(
        self,
        raw_response: Dict[str, Any],
        target_date: dt.date,
    ) -> List[Dict[str, Any]]:
        """Parse OWM forecast response into 6 time-range blocks for a target date.

        Groups 3-hour intervals by TIME_RANGES and computes representative values
        for each block: average temperature, feels_like, humidity, rain presence,
        and heat_alert (Req 3.5: temperature >= 35°C).

        Returns:
            List of 6 dicts, one per time range, with keys:
            time_range, start_time, end_time, temperature, feels_like,
            humidity, rain, heat_alert
        """
        # Collect data points per time range
        range_data: Dict[str, List[Dict[str, Any]]] = {label: [] for label in TIME_RANGES}

        forecast_list = raw_response.get("list", [])
        for item in forecast_list:
            # Parse the forecast timestamp (UTC) and convert to KST
            dt_utc = dt.datetime.fromtimestamp(item["dt"], tz=dt.timezone.utc)
            dt_kst = dt_utc.astimezone(KST)

            # Only include data points for the target date
            if dt_kst.date() != target_date:
                continue

            hour = dt_kst.hour
            time_range_label = get_time_range(hour)

            main = item.get("main", {})
            weather_list = item.get("weather", [])
            rain_data = item.get("rain", {})

            range_data[time_range_label].append({
                "temperature": main.get("temp", 0.0),
                "feels_like": main.get("feels_like", 0.0),
                "humidity": main.get("humidity", 0),
                "rain": bool(rain_data.get("3h", 0) > 0) or any(
                    w.get("main", "").lower() == "rain" for w in weather_list
                ),
            })

        # Build time blocks with averages (or defaults when no data)
        time_blocks: List[Dict[str, Any]] = []
        for label, (start_hour, end_hour) in TIME_RANGES.items():
            data_points = range_data[label]

            if data_points:
                avg_temp = round(
                    sum(d["temperature"] for d in data_points) / len(data_points), 1
                )
                avg_feels = round(
                    sum(d["feels_like"] for d in data_points) / len(data_points), 1
                )
                avg_humidity = round(
                    sum(d["humidity"] for d in data_points) / len(data_points)
                )
                has_rain = any(d["rain"] for d in data_points)
            else:
                # No data for this time block — use neutral defaults
                avg_temp = 0.0
                avg_feels = 0.0
                avg_humidity = 0
                has_rain = False

            # Req 3.5: heat_alert = true if temperature >= 35°C
            heat_alert = avg_temp >= 35.0

            # Clamp humidity to 0-100 range
            avg_humidity = max(0, min(100, avg_humidity))

            # Build start/end times for the block
            start_time = dt.datetime(
                target_date.year, target_date.month, target_date.day,
                start_hour, 0, 0, tzinfo=KST
            )
            end_time = dt.datetime(
                target_date.year, target_date.month, target_date.day,
                end_hour, 59, 59, tzinfo=KST
            )

            time_blocks.append({
                "time_range": label,
                "start_time": start_time,
                "end_time": end_time,
                "temperature": Decimal(str(avg_temp)),
                "feels_like": Decimal(str(avg_feels)),
                "humidity": avg_humidity,
                "rain": has_rain,
                "heat_alert": heat_alert,
            })

        return time_blocks
