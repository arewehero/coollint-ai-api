import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    morning_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daytime_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    night_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    irregular_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stay_home_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outing_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cooling_need_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saving_priority_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saving_opportunity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heat_gain_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cooling_loss_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ventilation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
