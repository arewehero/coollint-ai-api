"""프로필 API 테스트. (담당: 김지영)"""
import pytest


class TestProfileAPI:
    """프로필 저장/조회 API 테스트."""

    @pytest.mark.asyncio
    async def test_put_profile_success(self):
        """전체 프로필 저장 성공."""
        # TODO: httpx AsyncClient 기반 테스트 구현
        pass

    @pytest.mark.asyncio
    async def test_put_profile_invalid_enum(self):
        """잘못된 enum 값은 422 반환."""
        pass

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self):
        """프로필 미입력 시 404 반환."""
        pass

    @pytest.mark.asyncio
    async def test_patch_home_environment(self):
        """집 환경만 부분 수정."""
        pass

    @pytest.mark.asyncio
    async def test_patch_lifestyle(self):
        """생활패턴만 수정 시 analysis_recommended=true."""
        pass
