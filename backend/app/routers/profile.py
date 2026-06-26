from fastapi import APIRouter, Request, Depends
from uuid import UUID

from app.schemas.common import SuccessResponse
from app.schemas.profile import FullProfileRequest
from app.core.security import get_current_user_id

router = APIRouter()


@router.put("", response_model=SuccessResponse)
async def upsert_profile(request: Request, body: FullProfileRequest, user_id: UUID = Depends(get_current_user_id)):
    """집 환경, 생활패턴, 냉난방 및 전기요금 정보를 한 번에 저장."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"user_id": str(user_id), "profile_completed": True},
        meta={"request_id": request.state.request_id},
    )


@router.get("", response_model=SuccessResponse)
async def get_profile(request: Request, user_id: UUID = Depends(get_current_user_id)):
    """저장된 사용자 프로필 조회."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data=None,
        meta={"request_id": request.state.request_id},
    )


@router.patch("/home-environment", response_model=SuccessResponse)
async def patch_home_environment(request: Request, body: dict, user_id: UUID = Depends(get_current_user_id)):
    """집 환경만 수정."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"updated_fields": list(body.keys())},
        meta={"request_id": request.state.request_id},
    )


@router.patch("/lifestyle", response_model=SuccessResponse)
async def patch_lifestyle(request: Request, body: dict, user_id: UUID = Depends(get_current_user_id)):
    """생활패턴만 수정."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"updated_fields": list(body.keys()), "analysis_recommended": True},
        meta={"request_id": request.state.request_id},
    )


@router.patch("/energy", response_model=SuccessResponse)
async def patch_energy(request: Request, body: dict, user_id: UUID = Depends(get_current_user_id)):
    """냉난방 및 요금 정보만 수정."""
    # TODO: 실제 서비스 로직 연결
    return SuccessResponse(
        data={"updated_fields": list(body.keys()), "recalculation_recommended": True},
        meta={"request_id": request.state.request_id},
    )
