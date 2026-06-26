import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Integer, Numeric, Date, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ActionCompletionLog(Base):
    __tablename__ = "action_completion_logs"
    __table_args__ = (
        Index("ix_action_completion_logs_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recommendation_actions.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # completed / uncompleted
    saving_krw_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    energy_kwh_delta: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    co2_kg_delta: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)


class SavingSummary(Base):
    __tablename__ = "saving_summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # today / week / month
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    completed_action_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_saving_krw: Mapped[int] = mapped_column(Integer, nullable=False)
    total_energy_saving_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    total_co2_reduction_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    monthly_projected_saving_krw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
