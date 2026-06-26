"""날씨 Provider 인터페이스."""
from abc import ABC, abstractmethod
from typing import Any


class WeatherProvider(ABC):
    """날씨 API 제공자 기본 인터페이스."""

    @abstractmethod
    async def fetch_forecast(self, latitude: float, longitude: float) -> dict[str, Any]:
        """3시간 단위 예보 데이터를 조회한다."""
        ...
