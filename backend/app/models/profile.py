import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Integer, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    monthly_electricity_bill: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_goal_bill: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comfort_preference: Mapped[str] = mapped_column(String(30), nullable=False)
    ac_type: Mapped[str] = mapped_column(String(20), nullable=False)
    has_fan: Mapped[bool] = mapped_column(Boolean, nullable=False)
    curtain_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ac_power_watt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room_size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_temperature_setting: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    daily_ac_usage_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    electricity_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
