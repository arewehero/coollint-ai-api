from fastapi import APIRouter, Request, Depends
from uuid import UUID

from app.schemas.common import SuccessResponse
from app.schemas.user import AnonymousUserRequest
from app.core.security import get_current_user_id

router = APIRouter()


@router.post("/anonymous", status_code=201, response_model=SuccessResponse)
async def create_anonymous_user(request: Request, body: AnonymousUserRequest):
    """익명 사용자 생성."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"user_id": "placeholder", "user_type": "anonymous", "created_at": "2026-06-26T06:00:00+09:00"},
        meta={"request_id": request.state.request_id},
    )


@router.get("/me", response_model=SuccessResponse)
async def get_me(request: Request, user_id: UUID = Depends(get_current_user_id)):
    """현재 사용자 조회."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"id": str(user_id), "user_type": "anonymous", "has_profile": False, "created_at": "2026-06-26T06:00:00+09:00"},
        meta={"request_id": request.state.request_id},
    )
