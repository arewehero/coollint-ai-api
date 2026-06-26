"""AI Gateway 클라이언트 인터페이스. (담당: 임혜성 + AI 담당자)"""
from typing import Any

from pydantic import BaseModel


class LifestyleAnalysisResult(BaseModel):
    primary_type: str
    secondary_type: str | None
    confidence: float
    summary: str
    reason: str


class RecommendationCopyResult(BaseModel):
    cheer_message: str
    recommendations: list[dict[str, str]]


class CoolLinkAIClient:
    """백엔드가 AI 모듈을 호출하는 인터페이스.
    실제 구현이 Bedrock이든 mock이든 백엔드 비즈니스 로직은 바뀌지 않아야 한다.
    """

    async def analyze_lifestyle(self, payload: dict[str, Any]) -> LifestyleAnalysisResult:
        """생활 유형 판단 AI 호출."""
        # TODO: AWS Bedrock 연동 구현
        # Fallback: 점수 기반 deterministic 판단
        raise NotImplementedError

    async def generate_daily_plan_copy(self, payload: dict[str, Any]) -> RecommendationCopyResult:
        """추천 문구 생성 AI 호출."""
        # TODO: AWS Bedrock 연동 구현
        # Fallback: action_type별 기본 템플릿
        raise NotImplementedError
