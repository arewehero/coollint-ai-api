from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.core.errors import api_meta_from_request
from app.dependencies import get_ai_client_dependency, get_current_user_id
from app.schemas.ai import LifestyleAnalysisEndpointResponse, LifestyleAnalysisRequest
from app.schemas.common import ApiSuccessResponse
from app.services.ai_client import AIClient


router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/lifestyle-analysis", response_model=ApiSuccessResponse[LifestyleAnalysisEndpointResponse])
def analyze_lifestyle(
    request_body: LifestyleAnalysisRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    ai_client: AIClient = Depends(get_ai_client_dependency),
) -> ApiSuccessResponse[LifestyleAnalysisEndpointResponse]:
    ai_response = ai_client.analyze_lifestyle(
        {
            "user_id": str(user_id),
            "date": request_body.date,
            "score_snapshot_id": str(request_body.score_snapshot_id) if request_body.score_snapshot_id else None,
            "profile": request_body.profile,
            "scores": request_body.scores,
            "weather": request_body.weather,
        }
    )
    response = LifestyleAnalysisEndpointResponse(analysis_id=uuid.uuid4(), **ai_response.model_dump())
    return ApiSuccessResponse(data=response, meta=api_meta_from_request(request, include_generated_at=True))
