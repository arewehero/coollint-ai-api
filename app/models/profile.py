"""Profile domain models: HomeEnvironment, LifestyleInput, UserProfile.

Each table has a UNIQUE constraint on user_id to support upsert semantics.
Requirements: 2.1, 2.5, 2.6, 2.7
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HomeEnvironment(Base):
    __tablename__ = "home_environments"
    __table_args__ = (
        Index("uq_home_environments_user_id", "user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    housing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    floor_level: Mapped[str] = mapped_column(String(10), nullable=False)
    building_age: Mapped[str] = mapped_column(String(10), nullable=False)
    insulation_level: Mapped[str] = mapped_column(String(10), nullable=False)
    window_size: Mapped[str] = mapped_column(String(10), nullable=False)
    ventilation_level: Mapped[str] = mapped_column(String(10), nullable=False)
    window_sealing: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LifestyleInput(Base):
    __tablename__ = "lifestyle_inputs"
    __table_args__ = (
        Index("uq_lifestyle_inputs_user_id", "user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    main_activity_time: Mapped[str] = mapped_column(String(20), nullable=False)
    daytime_home_stay: Mapped[str] = mapped_column(String(20), nullable=False)
    sleep_time: Mapped[str] = mapped_column(String(10), nullable=False)
    outdoor_activity: Mapped[str] = mapped_column(String(10), nullable=False)
    hot_time_home_stay: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        Index("uq_user_profiles_user_id", "user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    monthly_electricity_bill: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_goal_bill: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comfort_preference: Mapped[str] = mapped_column(String(20), nullable=False)
    ac_type: Mapped[str] = mapped_column(String(10), nullable=False)
    has_fan: Mapped[bool] = mapped_column(Boolean, nullable=False)
    curtain_type: Mapped[str] = mapped_column(String(10), nullable=False)
    ac_power_watt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    room_size: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    current_temperature_setting: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    daily_ac_usage_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    electricity_unit_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(7, 2), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
