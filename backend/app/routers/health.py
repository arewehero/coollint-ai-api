from fastapi import APIRouter, Request

from app.schemas.common import SuccessResponse

router = APIRouter()


@router.get("/health", response_model=SuccessResponse)
async def health_check(request: Request):
    return SuccessResponse(
        data={"status": "ok", "service": "coollink-api", "version": "0.3"},
        meta={"request_id": request.state.request_id},
    )
