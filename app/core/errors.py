from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.time import now_kst
from app.schemas.common import ApiErrorBody, ApiFailureResponse, ApiMeta


class ApiException(Exception):
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
