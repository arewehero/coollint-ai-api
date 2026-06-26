from fastapi import APIRouter, Request, Depends

from app.schemas.common import SuccessResponse
from app.core.security import verify_internal_token

router = APIRouter()


@router.post("/jobs/generate-daily-recommendations", response_model=SuccessResponse, dependencies=[Depends(verify_internal_token)])
async def generate_daily_recommendations(request: Request, body: dict):
    """매일 오전 6시 추천 생성 내부 Job."""
    # TODO: 실제 배치 로직 연결
    return SuccessResponse(
        data={"date": body.get("date"), "target": body.get("target"), "generated_count": 0},
        meta={"request_id": request.state.request_id},
    )


@router.post("/ai/daily-plan-copy", response_model=SuccessResponse, dependencies=[Depends(verify_internal_token)])
async def ai_daily_plan_copy(request: Request, body: dict):
    """AI 추천 문구 생성 내부 API."""
    # TODO: 실제 AI Gateway 로직 연결
    return SuccessResponse(
        data={"daily_summary": {"cheer_message": ""}, "recommendations": []},
        meta={"request_id": request.state.request_id},
    )
