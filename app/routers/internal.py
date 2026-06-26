from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import api_meta_from_request
from app.dependencies import get_db, get_internal_job_service, verify_internal_job_token
from app.schemas.common import ApiSuccessResponse
from app.schemas.internal import GenerateDailyRecommendationsJobRequest, GenerateDailyRecommendationsJobResponse
from app.services.internal_job_service import GenerateDailyRecommendationsJobService


router = APIRouter(prefix="/internal/jobs", tags=["Internal"])


@router.post(
    "/generate-daily-recommendations",
    response_model=ApiSuccessResponse[GenerateDailyRecommendationsJobResponse],
    dependencies=[Depends(verify_internal_job_token)],
)
def generate_daily_recommendations(
    request_body: GenerateDailyRecommendationsJobRequest,
    request: Request,
    db: Session = Depends(get_db),
    service: GenerateDailyRecommendationsJobService = Depends(get_internal_job_service),
) -> ApiSuccessResponse[GenerateDailyRecommendationsJobResponse]:
    result = service.run(db, request_data=request_body)
    return ApiSuccessResponse(data=result, meta=api_meta_from_request(request, include_generated_at=True))
