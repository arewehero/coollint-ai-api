"""추천 플랜 생성/조회 서비스. (담당: 임혜성)"""


class RecommendationService:
    """오늘의 추천 플랜 생성 및 조회를 담당한다."""

    async def create_daily_plan(self, user_id: str, date: str, location: dict | None = None, force_regenerate: bool = False):
        """플랜 생성 전체 흐름 조합."""
        # TODO: 구현 - 프로필 확인, 날씨 조회, 점수 계산, AI 호출, 저장
        pass

    async def get_daily_plan(self, user_id: str, date: str):
        """저장된 플랜 조회."""
        # TODO: 구현
        pass
