import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LifestyleInput(Base):
    __tablename__ = "lifestyle_inputs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    main_activity_time: Mapped[str] = mapped_column(String(20), nullable=False)
    daytime_home_stay: Mapped[str] = mapped_column(String(20), nullable=False)
    sleep_time: Mapped[str] = mapped_column(String(20), nullable=False)
    outdoor_activity: Mapped[str] = mapped_column(String(20), nullable=False)
    hot_time_home_stay: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
