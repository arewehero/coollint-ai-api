from __future__ import annotations

import datetime as dt
from uuid import UUID

from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.errors import api_meta_from_request
from app.dependencies import get_current_user_id, get_daily_recommendation_service, get_db
from app.schemas.common import ApiSuccessResponse
from app.schemas.recommendation import DailyPlanResponse, GenerateDailyPlanRequest, ToggleActionRequest, ToggleActionResponse
from app.services.recommendation_service import DailyRecommendationService


router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post("/daily", response_model=ApiSuccessResponse[DailyPlanResponse], status_code=status.HTTP_201_CREATED)
def create_daily_recommendation(
    request_body: GenerateDailyPlanRequest,
    request: Request,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    service: DailyRecommendationService = Depends(get_daily_recommendation_service),
) -> ApiSuccessResponse[DailyPlanResponse]:
    daily_plan, created = service.create_daily_plan(db, user_id=user_id, request_data=request_body)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return ApiSuccessResponse(data=daily_plan, meta=api_meta_from_request(request, include_generated_at=True))


@router.get("/daily", response_model=ApiSuccessResponse[DailyPlanResponse])
def get_daily_recommendation(
    request: Request,
    date: Optional[dt.date] = None,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    service: DailyRecommendationService = Depends(get_daily_recommendation_service),
) -> ApiSuccessResponse[DailyPlanResponse]:
    daily_plan = service.get_daily_plan(db, user_id=user_id, target_date=date)
    return ApiSuccessResponse(data=daily_plan, meta=api_meta_from_request(request, include_generated_at=True))


@router.patch("/actions/{action_id}", response_model=ApiSuccessResponse[ToggleActionResponse])
def toggle_recommendation_action(
    action_id: UUID,
    request_body: ToggleActionRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    service: DailyRecommendationService = Depends(get_daily_recommendation_service),
) -> ApiSuccessResponse[ToggleActionResponse]:
    result = service.toggle_action(db, user_id=user_id, action_id=action_id, request_data=request_body)
    return ApiSuccessResponse(data=result, meta=api_meta_from_request(request, include_generated_at=True))
