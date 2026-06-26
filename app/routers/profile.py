"""Profile router: PUT /api/v1/profile for full profile upsert.

Requirements: 2.1, 2.5, 2.6, 2.7
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import api_meta_from_request
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.repositories.profile_repository import ProfileRepository
from app.schemas.common import ApiSuccessResponse
from app.schemas.profile import (
    EnergyProfileSchema,
    FullProfileRequest,
    FullProfileResponse,
    HomeEnvironmentSchema,
    LifestyleSchema,
)


router = APIRouter(prefix="/profile", tags=["Profile"])


def get_profile_repository() -> ProfileRepository:
    return ProfileRepository()


@router.put("", response_model=ApiSuccessResponse[FullProfileResponse])
def upsert_profile(
    request: Request,
    body: FullProfileRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    repo: ProfileRepository = Depends(get_profile_repository),
) -> ApiSuccessResponse[FullProfileResponse]:
    """Save or update the full profile (home_environment + lifestyle + energy_profile).

    Upserts all three profile tables for the authenticated user.
    Returns 200 OK with the stored profile data.
    """
    home = repo.upsert_home_environment(db, user_id, body.home_environment)
    lifestyle = repo.upsert_lifestyle_input(db, user_id, body.lifestyle)
    energy = repo.upsert_energy_profile(db, user_id, body.energy_profile)
    db.commit()
    db.refresh(home)
    db.refresh(lifestyle)
    db.refresh(energy)

    response_data = FullProfileResponse(
        home_environment=HomeEnvironmentSchema.model_validate(home),
        lifestyle=LifestyleSchema.model_validate(lifestyle),
        energy_profile=EnergyProfileSchema.model_validate(energy),
    )

    return ApiSuccessResponse(
        data=response_data,
        meta=api_meta_from_request(request),
    )
