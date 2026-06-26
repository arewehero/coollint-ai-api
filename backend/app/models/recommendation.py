import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Integer, Boolean, Text, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RecommendationPlan(Base):
    __tablename__ = "recommendation_plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    lifestyle_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lifestyle_analysis.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # generated / fallback / failed
    total_estimated_saving_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_estimated_saving_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_energy_saving_kwh: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=0, nullable=False)
    total_co2_reduction_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=0, nullable=False)
    cheer_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(20), nullable=False)  # ai / fallback / manual
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RecommendationAction(Base):
    __tablename__ = "recommendation_actions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recommendation_plans.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time_range: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_saving_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_energy_saving_kwh: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=0, nullable=False)
    estimated_co2_reduction_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=0, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_score: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=0, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
