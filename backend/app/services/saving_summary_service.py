"""절약 요약 서비스. (담당: 임혜성)"""


class SavingSummaryService:
    """오늘/주간/월간 절약 요약을 집계한다."""

    async def get_summary(self, user_id: str, period: str, date: str | None = None):
        """기간별 절약 요약 반환."""
        # TODO: 구현
        pass

    async def get_calendar(self, user_id: str, month: str):
        """월간 캘린더 요약 반환."""
        # TODO: 구현
        pass
