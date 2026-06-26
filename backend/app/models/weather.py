import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Integer, Boolean, Numeric, Date, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"
    __table_args__ = (
        Index("ix_weather_snapshots_date_expires_at", "date", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    region_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)


class WeatherTimeBlock(Base):
    __tablename__ = "weather_time_blocks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    weather_snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("weather_snapshots.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time_range: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime] = mapped_column(nullable=False)
    temperature: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    feels_like: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    humidity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uv_index: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    heat_alert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weather_risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
