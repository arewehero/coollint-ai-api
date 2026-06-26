from uuid import UUID

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def get_current_user_id(x_user_id: str = Header(..., alias="X-User-Id")) -> UUID:
    """X-User-Id 헤더에서 사용자 UUID를 추출한다."""
    try:
        return UUID(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 사용자 ID입니다.",
        )


async def verify_internal_token(x_internal_job_token: str = Header(..., alias="X-Internal-Job-Token")) -> None:
    """내부 Job API 토큰 검증."""
    if x_internal_job_token != settings.INTERNAL_JOB_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="내부 토큰이 유효하지 않습니다.",
        )
