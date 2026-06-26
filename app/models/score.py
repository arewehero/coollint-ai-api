from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"
    __table_args__ = (
        Index("uq_score_snapshots_user_date", "user_id", "date", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    morning_score: Mapped[int] = mapped_column(Integer, nullable=False)
    daytime_score: Mapped[int] = mapped_column(Integer, nullable=False)
    night_score: Mapped[int] = mapped_column(Integer, nullable=False)
    irregular_score: Mapped[int] = mapped_column(Integer, nullable=False)
    stay_home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    outing_score: Mapped[int] = mapped_column(Integer, nullable=False)
    cooling_need_score: Mapped[int] = mapped_column(Integer, nullable=False)
    saving_priority_score: Mapped[int] = mapped_column(Integer, nullable=False)
    saving_opportunity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    heat_gain_score: Mapped[int] = mapped_column(Integer, nullable=False)
    cooling_loss_score: Mapped[int] = mapped_column(Integer, nullable=False)
    ventilation_score: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_scores: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
