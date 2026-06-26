from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field


DataT = TypeVar("DataT")


class ApiMeta(BaseModel):
    request_id: Optional[str] = None
    generated_at: Optional[dt.datetime] = None


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ApiSuccessResponse(BaseModel, Generic[DataT]):
    success: Literal[True] = True
    data: DataT
    meta: Optional[ApiMeta] = None


class ApiFailureResponse(BaseModel):
    success: Literal[False] = False
    error: ApiErrorBody
    meta: Optional[ApiMeta] = None
