from fastapi import APIRouter, Request

from app.schemas.common import SuccessResponse
from app.schemas.calculation import EstimateRequest

router = APIRouter()


@router.post("/estimate", response_model=SuccessResponse)
async def estimate_savings(request: Request, body: EstimateRequest):
    """전력량·요금 시뮬레이션."""
    # TODO: 실제 계산 로직 연결
    return SuccessResponse(
        data={"current": {}, "target": {}, "saving": {}, "assumptions": {}},
        meta={"request_id": request.state.request_id},
    )
