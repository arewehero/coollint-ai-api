from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MetaResponse(BaseModel):
    request_id: str | None = None
    generated_at: datetime | None = None


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None
    meta: MetaResponse | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody
    meta: MetaResponse | None = None
