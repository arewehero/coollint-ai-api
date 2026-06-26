from fastapi import APIRouter, Request, Depends, Query
from uuid import UUID

from app.schemas.common import SuccessResponse
from app.schemas.recommendation import DailyPlanRequest, ActionCompleteRequest
from app.core.security import get_current_user_id

router = APIRouter()


@router.post("/daily", status_code=201, response_model=SuccessResponse)
async def create_daily_plan(request: Request, body: DailyPlanRequest, user_id: UUID = Depends(get_current_user_id)):
    """오늘의 절약 행동 추천 생성."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"plan_id": "placeholder", "date": body.date, "status": "generated", "actions": []},
        meta={"request_id": request.state.request_id},
    )


@router.get("/daily", response_model=SuccessResponse)
async def get_daily_plan(request: Request, user_id: UUID = Depends(get_current_user_id), date: str | None = Query(None)):
    """오늘의 추천 플랜 조회."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data=None,
        meta={"request_id": request.state.request_id},
    )


@router.patch("/actions/{action_id}", response_model=SuccessResponse)
async def complete_action(request: Request, action_id: str, body: ActionCompleteRequest, user_id: UUID = Depends(get_current_user_id)):
    """행동 완료/취소."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"action_id": action_id, "is_completed": body.is_completed},
        meta={"request_id": request.state.request_id},
    )
