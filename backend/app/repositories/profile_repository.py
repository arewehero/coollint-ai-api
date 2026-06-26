"""프로필(집 환경, 생활패턴, 요금 정보) DB 조작."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.profile import UserProfile
from app.models.home_environment import HomeEnvironment
from app.models.lifestyle_input import LifestyleInput


class ProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_profile(self, user_id: UUID) -> UserProfile | None:
        result = await self.session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_home_environment(self, user_id: UUID) -> HomeEnvironment | None:
        result = await self.session.execute(select(HomeEnvironment).where(HomeEnvironment.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_lifestyle_input(self, user_id: UUID) -> LifestyleInput | None:
        result = await self.session.execute(select(LifestyleInput).where(LifestyleInput.user_id == user_id))
        return result.scalar_one_or_none()
