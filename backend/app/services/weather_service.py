"""날씨 조회, 캐싱, 시간대 블록 매핑 서비스."""


class WeatherService:
    """날씨 데이터 조회 및 캐싱을 담당한다. (담당: 이태우)"""

    async def get_hourly_weather(self, date: str, latitude: float | None, longitude: float | None, region_name: str | None, force_refresh: bool = False):
        """캐시 확인 후 시간대별 날씨 반환."""
        # TODO: 구현
        pass

    async def refresh_weather(self, date: str, latitude: float | None, longitude: float | None, region_name: str | None):
        """날씨를 강제로 새로 조회한다."""
        # TODO: 구현
        pass
