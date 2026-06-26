"""AI router — AI-powered lifestyle analysis endpoint.

POST /api/v1/ai/lifestyle-analysis performs AI-based lifestyle type analysis
with profile/score validation, AI call with fallback, and DB persistence.

Requirements: 5.1, 5.2, 5.3, 5.5, 5.6, 5.7
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import api_meta_from_request
from app.core.time_utils import parse_date
from app.db.session import get_db
from app.dependencies import (
    get_ai_client_dependency,
    get_current_user_id,
    get_profile_repository,
    get_score_repository,
)
from app.repositories.profile_repository import ProfileRepository
from app.repositories.score_repository import ScoreRepository
from app.routers.analysis import perform_lifestyle_analysis
from app.schemas.analysis import LifestyleAnalysisResponse
from app.schemas.common import ApiSuccessResponse
from app.services.ai_client import AIClient


router = APIRouter(prefix="/ai", tags=["AI"])


@router.post(
    "/lifestyle-analysis",
    response_model=ApiSuccessResponse[LifestyleAnalysisResponse],
    summary="AI 생활유형 분석",
    description="프로필과 점수를 기반으로 AI가 생활유형을 판단합니다. AI 실패 시 점수 기반 폴백을 적용합니다.",
)
def analyze_lifestyle(
    request: Request,
    date: Optional[str] = None,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
    score_repo: ScoreRepository = Depends(get_score_repository),
    ai_client: AIClient = Depends(get_ai_client_dependency),
) -> ApiSuccessResponse[LifestyleAnalysisResponse]:
    """AI lifestyle analysis endpoint.

    Flow:
    1. Parse date (defaults to today KST) — Req 11.2
    2. Delegate to perform_lifestyle_analysis (profile+score check → AI → fallback → DB upsert)
    3. Return LifestyleAnalysisResponse

    Requirements: 5.1, 5.2, 5.3, 5.5, 5.6, 5.7
    """
    # 1. Parse date (defaults to today KST)
    target_date = parse_date(date)

    # 2. Perform analysis (checks profile, scores, calls AI, handles fallback, upserts DB)
    analysis = perform_lifestyle_analysis(
        user_id=user_id,
        target_date=target_date,
        db=db,
        profile_repo=profile_repo,
        score_repo=score_repo,
        ai_client=ai_client,
    )

    # 3. Return response
    response_data = LifestyleAnalysisResponse.model_validate(analysis)
    return ApiSuccessResponse(
        data=response_data,
        meta=api_meta_from_request(request, include_generated_at=True),
    )
