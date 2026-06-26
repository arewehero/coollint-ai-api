from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.core.errors import ApiException
from app.core.time import today_kst
from app.repositories.profile_repository import ProfileRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.internal import (
    GenerateDailyRecommendationsJobRequest,
    GenerateDailyRecommendationsJobResponse,
    InternalJobErrorResponse,
)
from app.schemas.recommendation import GenerateDailyPlanRequest
from app.services.recommendation_service import DailyRecommendationService


class GenerateDailyRecommendationsJobService:
    def __init__(
        self,
        *,
        profile_repository: ProfileRepository,
        recommendation_repository: RecommendationRepository,
        daily_recommendation_service: DailyRecommendationService,
    ) -> None:
        self.profile_repository = profile_repository
        self.recommendation_repository = recommendation_repository
        self.daily_recommendation_service = daily_recommendation_service

    def run(
        self,
        db: Session,
        *,
        request_data: GenerateDailyRecommendationsJobRequest,
    ) -> GenerateDailyRecommendationsJobResponse:
        if request_data.target != "all_active_users":
            raise ApiException(status_code=400, code="INVALID_PROFILE_INPUT", message="지원하지 않는 job target입니다.")

        target_date = request_data.date or today_kst()
        user_ids = self.profile_repository.list_active_user_ids_with_profiles(db)
        generated_count = 0
        skipped_count = 0
        errors: List[InternalJobErrorResponse] = []

        for user_id in user_ids:
            existing_plan = self.recommendation_repository.get_daily_plan(db, user_id, target_date)
            if existing_plan is not None:
                skipped_count += 1
                continue

            if request_data.dry_run:
                generated_count += 1
                continue

            try:
                self.daily_recommendation_service.create_daily_plan(
                    db,
                    user_id=user_id,
                    request_data=GenerateDailyPlanRequest(date=target_date, force_regenerate=False),
                )
                generated_count += 1
            except ApiException as exc:
                _rollback_if_possible(db)
                errors.append(InternalJobErrorResponse(user_id=str(user_id), error_code=exc.code, message=exc.message))
            except Exception as exc:
                _rollback_if_possible(db)
                errors.append(InternalJobErrorResponse(user_id=str(user_id), error_code="UNKNOWN_ERROR", message=str(exc)))

        return GenerateDailyRecommendationsJobResponse(
            date=target_date,
            target=request_data.target,
            total_users=len(user_ids),
            generated_count=generated_count,
            skipped_count=skipped_count,
            failed_count=len(errors),
            errors=errors,
        )


def _rollback_if_possible(db: Session) -> None:
    rollback = getattr(db, "rollback", None)
    if callable(rollback):
        rollback()
