"""날씨 스냅샷 DB 조작."""
from uuid import UUID
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.weather import WeatherSnapshot


class WeatherRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest_snapshot(self, target_date: date, user_id: UUID | None = None) -> WeatherSnapshot | None:
        query = select(WeatherSnapshot).where(WeatherSnapshot.date == target_date)
        if user_id:
            query = query.where(WeatherSnapshot.user_id == user_id)
        query = query.order_by(WeatherSnapshot.fetched_at.desc()).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
