from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header

from app.core.config import settings
from app.core.errors import ApiException, ErrorCode
from app.core.security import get_current_user_id  # noqa: F401 — re-export for backward compat
from app.db.session import get_db
from app.repositories.profile_repository import ProfileRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.score_repository import ScoreRepository
from app.services.ai_client import AIClient, get_ai_client
from app.services.external_adapters import MockScoringAdapter, MockWeatherAdapter
from app.services.internal_job_service import GenerateDailyRecommendationsJobService
from app.services.recommendation_candidate_service import RecommendationCandidateService
from app.services.recommendation_service import DailyRecommendationService
from app.services.saving_summary_service import SavingSummaryService


def verify_internal_job_token(x_internal_job_token: Optional[str] = Header(None, alias="X-Internal-Job-Token")) -> None:
    if not settings.internal_job_token or x_internal_job_token != settings.internal_job_token:
        raise ApiException(
            status_code=ErrorCode.UNAUTHORIZED.http_status,
            code=ErrorCode.UNAUTHORIZED.code,
            message="내부 Job 토큰이 유효하지 않습니다.",
        )


def get_profile_repository() -> ProfileRepository:
    return ProfileRepository()


def get_score_repository() -> ScoreRepository:
    return ScoreRepository()


def get_recommendation_repository() -> RecommendationRepository:
    return RecommendationRepository()


def get_weather_adapter() -> MockWeatherAdapter:
    return MockWeatherAdapter()


def get_scoring_adapter() -> MockScoringAdapter:
    return MockScoringAdapter()


def get_candidate_service() -> RecommendationCandidateService:
    return RecommendationCandidateService()


def get_ai_client_dependency() -> AIClient:
    return get_ai_client()


def get_daily_recommendation_service(
    profile_repository: ProfileRepository = Depends(get_profile_repository),
    recommendation_repository: RecommendationRepository = Depends(get_recommendation_repository),
    weather_adapter: MockWeatherAdapter = Depends(get_weather_adapter),
    scoring_adapter: MockScoringAdapter = Depends(get_scoring_adapter),
    candidate_service: RecommendationCandidateService = Depends(get_candidate_service),
    ai_client: AIClient = Depends(get_ai_client_dependency),
) -> DailyRecommendationService:
    return DailyRecommendationService(
        profile_repository=profile_repository,
        recommendation_repository=recommendation_repository,
        weather_adapter=weather_adapter,
        scoring_adapter=scoring_adapter,
        candidate_service=candidate_service,
        ai_client=ai_client,
    )


def get_saving_summary_service(
    profile_repository: ProfileRepository = Depends(get_profile_repository),
    recommendation_repository: RecommendationRepository = Depends(get_recommendation_repository),
) -> SavingSummaryService:
    return SavingSummaryService(
        profile_repository=profile_repository,
        recommendation_repository=recommendation_repository,
    )


def get_internal_job_service(
    profile_repository: ProfileRepository = Depends(get_profile_repository),
    recommendation_repository: RecommendationRepository = Depends(get_recommendation_repository),
    daily_recommendation_service: DailyRecommendationService = Depends(get_daily_recommendation_service),
) -> GenerateDailyRecommendationsJobService:
    return GenerateDailyRecommendationsJobService(
        profile_repository=profile_repository,
        recommendation_repository=recommendation_repository,
        daily_recommendation_service=daily_recommendation_service,
    )
