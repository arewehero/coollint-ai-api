from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LifestyleAnalysis(Base):
    __tablename__ = "lifestyle_analysis"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_lifestyle_analysis_confidence"),
        Index("uq_lifestyle_analysis_user_date", "user_id", "date", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    primary_type: Mapped[str] = mapped_column(String(30), nullable=False)
    secondary_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    raw_ai_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    plans: Mapped[List["RecommendationPlan"]] = relationship(back_populates="lifestyle_analysis")


class RecommendationPlan(Base):
    __tablename__ = "recommendation_plans"
    __table_args__ = (
        Index("uq_recommendation_plans_user_date", "user_id", "date", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    lifestyle_analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lifestyle_analysis.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    total_estimated_saving_krw: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    monthly_estimated_saving_krw: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_energy_saving_kwh: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False, server_default="0")
    total_co2_reduction_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False, server_default="0")
    cheer_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    lifestyle_analysis: Mapped[Optional["LifestyleAnalysis"]] = relationship(back_populates="plans")
    actions: Mapped[List["RecommendationAction"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RecommendationAction(Base):
    __tablename__ = "recommendation_actions"
    __table_args__ = (
        Index("idx_recommendation_actions_plan", "plan_id", "sort_order"),
        Index("idx_recommendation_actions_user_date", "user_id", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendation_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    time_range: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_saving_krw: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    estimated_energy_saving_kwh: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False, server_default="0")
    estimated_co2_reduction_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False, server_default="0")
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_score: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False, server_default="0")
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    completed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    plan: Mapped[RecommendationPlan] = relationship(back_populates="actions")
    completion_logs: Mapped[List["ActionCompletionLog"]] = relationship(
        back_populates="action",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ActionCompletionLog(Base):
    __tablename__ = "action_completion_logs"
    __table_args__ = (
        Index("idx_action_completion_logs_action", "action_id"),
        Index("idx_action_completion_logs_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendation_actions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    saving_krw_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    energy_kwh_delta: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    co2_kg_delta: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    action: Mapped[RecommendationAction] = relationship(back_populates="completion_logs")


class SavingSummary(Base):
    __tablename__ = "saving_summaries"
    __table_args__ = (
        Index("uq_saving_summaries_user_period", "user_id", "period_type", "period_start", "period_end", unique=True),
        Index("idx_saving_summaries_user_period_start", "user_id", "period_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[dt.date] = mapped_column(Date, nullable=False)
    period_end: Mapped[dt.date] = mapped_column(Date, nullable=False)
    completed_action_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_saving_krw: Mapped[int] = mapped_column(Integer, nullable=False)
    total_energy_saving_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    total_co2_reduction_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    monthly_projected_saving_krw: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AIGenerationLog(Base):
    __tablename__ = "ai_generation_logs"
    __table_args__ = (
        Index("idx_ai_generation_logs_user_created_at", "user_id", "created_at"),
        Index("idx_ai_generation_logs_request_type_created_at", "request_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(30), nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    request_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
