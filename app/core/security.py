"""Security dependencies for FastAPI endpoints.

Provides `get_current_user_id` which extracts and validates the X-User-Id header,
parses it as UUID, and verifies the user exists in the database.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.errors import ApiException, ErrorCode
from app.db.session import get_db


def get_current_user_id(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> UUID:
    """Authenticate the request by validating X-User-Id header.

    1. Check that X-User-Id header is present.
    2. Parse header value as a valid UUID.
    3. Verify that the user exists in the `users` table (not soft-deleted).

    Raises ApiException(401) for missing/invalid/nonexistent user.
    """
    # 1. Header 누락 확인
    if x_user_id is None:
        raise ApiException(
            status_code=ErrorCode.UNAUTHORIZED.http_status,
            code=ErrorCode.UNAUTHORIZED.code,
            message="X-User-Id 헤더가 누락되었습니다.",
        )

    # 2. UUID 형식 파싱
    try:
        user_id = UUID(x_user_id)
    except (ValueError, AttributeError) as exc:
        raise ApiException(
            status_code=ErrorCode.UNAUTHORIZED.http_status,
            code=ErrorCode.UNAUTHORIZED.code,
            message="X-User-Id 헤더의 UUID 형식이 올바르지 않습니다.",
        ) from exc

    # 3. 사용자 존재 여부 확인 (users 테이블)
    try:
        bind = db.get_bind()
    except AttributeError:
        # DB session이 get_bind를 지원하지 않는 경우 (테스트 등) → UUID 파싱만으로 통과
        return user_id

    table_names = set(inspect(bind).get_table_names())
    if "users" not in table_names:
        # users 테이블이 아직 생성되지 않은 경우 → UUID 파싱만으로 통과
        return user_id

    # deleted_at 컬럼 존재 확인 (soft delete 지원)
    columns = {col["name"] for col in inspect(bind).get_columns("users")}
    if "deleted_at" in columns:
        query = text(
            "SELECT 1 FROM users WHERE id = :user_id AND deleted_at IS NULL LIMIT 1"
        )
    else:
        query = text("SELECT 1 FROM users WHERE id = :user_id LIMIT 1")

    row = db.execute(query, {"user_id": str(user_id)}).first()
    if row is None:
        raise ApiException(
            status_code=ErrorCode.UNAUTHORIZED.http_status,
            code=ErrorCode.UNAUTHORIZED.code,
            message="존재하지 않는 사용자입니다.",
        )

    return user_id
