"""Weather repository for DB-based caching of weather snapshots.

Provides:
- get_cached_snapshot: returns non-expired snapshot for date/location
- get_expired_snapshot: returns the most recent expired snapshot for date/location
- save_snapshot: persists a new WeatherSnapshot with its time blocks

Requirements: 3.3, 3.4, 3.6
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.time import now_kst
from app.models.weather import WeatherSnapshot, WeatherTimeBlock


class WeatherRepository:
    """Repository for WeatherSnapshot persistence and cache queries."""

    def get_cached_snapshot(
        self,
        db: Session,
        date: dt.date,
        latitude: Decimal,
        longitude: Decimal,
    ) -> Optional[WeatherSnapshot]:
        """Return a non-expired cached WeatherSnapshot for given date/location.

        Returns None if no valid (expires_at > now) cache exists.
        Requirement 3.3.
        """
        current_time = now_kst()
        return (
            db.query(WeatherSnapshot)
            .filter(
                WeatherSnapshot.date == date,
                WeatherSnapshot.latitude == latitude,
                WeatherSnapshot.longitude == longitude,
                WeatherSnapshot.expires_at > current_time,
            )
            .order_by(WeatherSnapshot.fetched_at.desc())
            .first()
        )

    def get_expired_snapshot(
        self,
        db: Session,
        date: dt.date,
        latitude: Decimal,
        longitude: Decimal,
    ) -> Optional[WeatherSnapshot]:
        """Return the most recent expired WeatherSnapshot for given date/location.

        Used as fallback when the provider is unavailable.
        Requirement 3.6.
        """
        return (
            db.query(WeatherSnapshot)
            .filter(
                WeatherSnapshot.date == date,
                WeatherSnapshot.latitude == latitude,
                WeatherSnapshot.longitude == longitude,
            )
            .order_by(WeatherSnapshot.fetched_at.desc())
            .first()
        )

    def save_snapshot(
        self,
        db: Session,
        *,
        date: dt.date,
        latitude: Decimal,
        longitude: Decimal,
        region_name: Optional[str] = None,
        expires_at: dt.datetime,
        raw_response: Optional[Dict[str, Any]] = None,
        time_blocks_data: List[Dict[str, Any]],
    ) -> WeatherSnapshot:
        """Persist a new WeatherSnapshot with associated time blocks.

        Requirement 3.4: cache with 1-hour TTL (caller provides expires_at).
        """
        snapshot = WeatherSnapshot(
            id=uuid.uuid4(),
            date=date,
            latitude=latitude,
            longitude=longitude,
            region_name=region_name,
            provider="openweathermap",
            fetched_at=now_kst(),
            expires_at=expires_at,
            raw_response=raw_response,
        )

        for block_data in time_blocks_data:
            block = WeatherTimeBlock(
                id=uuid.uuid4(),
                weather_snapshot_id=snapshot.id,
                date=date,
                time_range=block_data["time_range"],
                start_time=block_data["start_time"],
                end_time=block_data["end_time"],
                temperature=block_data["temperature"],
                feels_like=block_data["feels_like"],
                humidity=block_data["humidity"],
                rain=block_data["rain"],
                heat_alert=block_data["heat_alert"],
                uv_index=block_data.get("uv_index"),
                weather_risk_score=block_data.get("weather_risk_score"),
            )
            snapshot.time_blocks.append(block)

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
