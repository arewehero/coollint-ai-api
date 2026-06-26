from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.time import now_kst
from app.schemas.common import ApiErrorBody, ApiFailureResponse, ApiMeta


# ---------------------------------------------------------------------------
# Error Code Catalog
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ErrorCodeEntry:
    """Immutable error code definition with HTTP status and code string."""

    code: str
    http_status: int
    default_message: str


class ErrorCode:
    """Centralized error code catalog.

    Each entry contains:
      - code: string code returned in the error response body
      - http_status: HTTP status code
      - default_message: default Korean error message
    """

    UNAUTHORIZED = _ErrorCodeEntry(
        code="UNAUTHORIZED",
        http_status=401,
        default_message="인증에 실패했습니다.",
    )
    FORBIDDEN = _ErrorCodeEntry(
        code="FORBIDDEN",
        http_status=403,
        default_message="해당 리소스에 대한 접근 권한이 없습니다.",
    )
    NOT_FOUND = _ErrorCodeEntry(
        code="NOT_FOUND",
        http_status=404,
        default_message="요청한 리소스를 찾을 수 없습니다.",
    )
    VALIDATION_ERROR = _ErrorCodeEntry(
        code="VALIDATION_ERROR",
        http_status=422,
        default_message="입력값 검증에 실패했습니다.",
    )
    PROFILE_REQUIRED = _ErrorCodeEntry(
        code="PROFILE_REQUIRED",
        http_status=422,
        default_message="프로필이 등록되지 않았습니다. 먼저 프로필을 등록해주세요.",
    )
    PREREQUISITE_MISSING = _ErrorCodeEntry(
        code="PREREQUISITE_MISSING",
        http_status=422,
        default_message="선행 데이터가 존재하지 않습니다.",
    )
    INVALID_DATE_FORMAT = _ErrorCodeEntry(
        code="INVALID_DATE_FORMAT",
        http_status=422,
        default_message="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요.",
    )
    INVALID_PERIOD = _ErrorCodeEntry(
        code="INVALID_PERIOD",
        http_status=400,
        default_message="period 파라미터는 today, week, month 중 하나여야 합니다.",
    )
    WEATHER_UNAVAILABLE = _ErrorCodeEntry(
        code="WEATHER_UNAVAILABLE",
        http_status=503,
        default_message="날씨 데이터를 조회할 수 없습니다.",
    )


# ---------------------------------------------------------------------------
# Exception Class
# ---------------------------------------------------------------------------


class ApiException(Exception):
    """Application-level exception that maps to a structured JSON error response."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}

    @classmethod
    def from_error_code(
        cls,
        error_code: _ErrorCodeEntry,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> "ApiException":
        """Create an ApiException from an ErrorCode catalog entry.

        Uses the entry's default_message if no custom message is provided.
        """
        return cls(
            status_code=error_code.http_status,
            code=error_code.code,
            message=message or error_code.default_message,
            details=details,
        )


# ---------------------------------------------------------------------------
# Helpers & Handler
# ---------------------------------------------------------------------------


def request_id_from_request(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


def api_meta_from_request(request: Request, include_generated_at: bool = False) -> ApiMeta:
    return ApiMeta(
        request_id=request_id_from_request(request),
        generated_at=now_kst() if include_generated_at else None,
    )


async def api_exception_handler(request: Request, exc: ApiException) -> JSONResponse:
    body = ApiFailureResponse(
        success=False,
        error=ApiErrorBody(code=exc.code, message=exc.message, details=exc.details),
        meta=api_meta_from_request(request),
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json", exclude_none=True))
