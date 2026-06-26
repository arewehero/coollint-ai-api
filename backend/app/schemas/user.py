from datetime import datetime

from pydantic import BaseModel


class AnonymousUserRequest(BaseModel):
    client_timezone: str = "Asia/Seoul"


class UserResponse(BaseModel):
    user_id: str
    user_type: str
    created_at: datetime


class UserMeResponse(BaseModel):
    id: str
    user_type: str
    has_profile: bool
    created_at: datetime
