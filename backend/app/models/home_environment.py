import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HomeEnvironment(Base):
    __tablename__ = "home_environments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    housing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    floor_level: Mapped[str] = mapped_column(String(20), nullable=False)
    building_age: Mapped[str] = mapped_column(String(20), nullable=False)
    insulation_level: Mapped[str] = mapped_column(String(20), nullable=False)
    window_size: Mapped[str] = mapped_column(String(20), nullable=False)
    ventilation_level: Mapped[str] = mapped_column(String(20), nullable=False)
    window_sealing: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
