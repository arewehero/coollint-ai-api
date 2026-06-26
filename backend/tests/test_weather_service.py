"""날씨 서비스 테스트. (담당: 이태우)"""
import pytest


class TestWeatherService:
    """날씨 캐시 hit/miss 및 시간대 매핑 테스트."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """캐시가 있으면 외부 API를 호출하지 않는다."""
        # TODO: mock provider 기반 테스트
        pass

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_external(self):
        """캐시가 없으면 외부 API를 호출한다."""
        pass

    @pytest.mark.asyncio
    async def test_time_block_mapping(self):
        """3시간 예보가 서비스 시간대 블록으로 매핑된다."""
        pass
