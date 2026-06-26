from fastapi import APIRouter, Request, Depends
from uuid import UUID

from app.schemas.common import SuccessResponse
from app.schemas.score import ScoreCalculationRequest
from app.schemas.analysis import LifestyleAnalysisRequest
from app.core.security import get_current_user_id

router = APIRouter()


@router.post("/scores", response_model=SuccessResponse)
async def calculate_scores(request: Request, body: ScoreCalculationRequest, user_id: UUID = Depends(get_current_user_id)):
    """사용자 입력과 날씨 기반으로 백엔드 점수를 계산."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"score_snapshot_id": "placeholder", "scores": {}, "dominant_signals": []},
        meta={"request_id": request.state.request_id},
    )


@router.post("/ai/lifestyle-analysis", response_model=SuccessResponse)
async def ai_lifestyle_analysis(request: Request, body: LifestyleAnalysisRequest, user_id: UUID = Depends(get_current_user_id)):
    """AI 생활패턴 분석."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"analysis_id": "placeholder", "primary_type": "", "secondary_type": None, "confidence": 0.0, "summary": ""},
        meta={"request_id": request.state.request_id},
    )
