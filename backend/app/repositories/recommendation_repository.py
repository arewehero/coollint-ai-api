"""추천 플랜/행동 DB 조작."""
from uuid import UUID
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.recommendation import RecommendationPlan, RecommendationAction


class RecommendationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_plan_by_user_date(self, user_id: UUID, target_date: date) -> RecommendationPlan | None:
        result = await self.session.execute(
            select(RecommendationPlan).where(
                RecommendationPlan.user_id == user_id,
                RecommendationPlan.date == target_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_action_by_id(self, action_id: UUID) -> RecommendationAction | None:
        result = await self.session.execute(
            select(RecommendationAction).where(RecommendationAction.id == action_id)
        )
        return result.scalar_one_or_none()
