"""절약 요약 DB 조작."""
from uuid import UUID
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.recommendation import RecommendationAction


class SavingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def sum_completed_savings(self, user_id: UUID, start_date: date, end_date: date) -> dict:
        result = await self.session.execute(
            select(
                func.count(RecommendationAction.id).label("count"),
                func.coalesce(func.sum(RecommendationAction.estimated_saving_krw), 0).label("total_krw"),
                func.coalesce(func.sum(RecommendationAction.estimated_energy_saving_kwh), 0).label("total_kwh"),
                func.coalesce(func.sum(RecommendationAction.estimated_co2_reduction_kg), 0).label("total_co2"),
            ).where(
                RecommendationAction.user_id == user_id,
                RecommendationAction.date >= start_date,
                RecommendationAction.date <= end_date,
                RecommendationAction.is_completed.is_(True),
            )
        )
        row = result.one()
        return {
            "count": row.count,
            "total_krw": row.total_krw,
            "total_kwh": float(row.total_kwh),
            "total_co2": float(row.total_co2),
        }
