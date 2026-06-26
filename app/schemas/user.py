from __future__ import annotations

import datetime as dt
from uuid import UUID

from pydantic import BaseModel


class AnonymousUserResponse(BaseModel):
    """Response schema for anonymous user creation."""

    user_id: UUID
    user_type: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}
