from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"
    __table_args__ = (
        Index("idx_weather_snapshots_date_expires_at", "date", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    region_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, server_default="openweathermap")
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    time_blocks: Mapped[List["WeatherTimeBlock"]] = relationship(
        back_populates="weather_snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WeatherTimeBlock(Base):
    __tablename__ = "weather_time_blocks"
    __table_args__ = (
        Index("idx_weather_time_blocks_snapshot_time_range", "weather_snapshot_id", "time_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    weather_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("weather_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    time_range: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temperature: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    feels_like: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    humidity: Mapped[int] = mapped_column(Integer, nullable=False)
    rain: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    uv_index: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    heat_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    weather_risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    weather_snapshot: Mapped[WeatherSnapshot] = relationship(back_populates="time_blocks")
