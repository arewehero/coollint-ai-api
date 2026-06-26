from __future__ import annotations

import datetime as dt
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ApiException
from app.core.time import now_kst, today_kst
from app.models import ActionCompletionLog, LifestyleAnalysis, RecommendationAction, RecommendationPlan
from app.repositories.profile_repository import ProfileRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.ai import DailyPlanActionCopyAIResponse
from app.schemas.recommendation import (
    DailyPlanResponse,
    DailySummaryResponse,
    GenerateDailyPlanRequest,
    LifestyleAnalysisResponse,
    RecommendationActionResponse,
    TodayProgressResponse,
    ToggleActionDeltaResponse,
    ToggleActionRequest,
    ToggleActionResponse,
)
from app.services.ai_client import AIClient, FallbackAIClient
from app.services.ai_logging import record_ai_generation_log
from app.services.external_adapters import MockScoringAdapter, MockWeatherAdapter
from app.services.recommendation_candidate_service import RecommendationCandidate, RecommendationCandidateService


class DailyRecommendationService:
    def __init__(
        self,
        *,
        profile_repository: ProfileRepository,
        recommendation_repository: RecommendationRepository,
        weather_adapter: MockWeatherAdapter,
        scoring_adapter: MockScoringAdapter,
        candidate_service: RecommendationCandidateService,
        ai_client: AIClient,
    ) -> None:
        self.profile_repository = profile_repository
        self.recommendation_repository = recommendation_repository
        self.weather_adapter = weather_adapter
        self.scoring_adapter = scoring_adapter
        self.candidate_service = candidate_service
        self.ai_client = ai_client

    def create_daily_plan(
        self,
        db: Session,
        *,
        user_id: UUID,
        request_data: GenerateDailyPlanRequest,
    ) -> Tuple[DailyPlanResponse, bool]:
        target_date = request_data.date or today_kst()
        profile = self.profile_repository.get_profile(db, user_id)
        if profile is None:
            raise ApiException(status_code=404, code="PROFILE_NOT_FOUND", message="사용자 프로필을 찾을 수 없습니다.")

        existing_plan = self.recommendation_repository.get_daily_plan(db, user_id, target_date)
        if existing_plan and not request_data.force_regenerate:
            return self.build_daily_plan_response(existing_plan), False
        if existing_plan and request_data.force_regenerate:
            if self.recommendation_repository.has_completed_actions(existing_plan):
                raise ApiException(
                    status_code=409,
                    code="ACTION_ALREADY_COMPLETED",
                    message="이미 완료된 행동이 있어 추천 플랜을 재생성할 수 없습니다.",
                )
            self.recommendation_repository.delete_plan(db, existing_plan)

        location = request_data.location.model_dump(exclude_none=True) if request_data.location else {}
        weather = self.weather_adapter.get_daily_weather(user_id=user_id, target_date=target_date, location=location)
        scores = self.scoring_adapter.calculate_scores(profile=profile, weather=weather)
        candidates = sort_candidates_by_priority(
            self.candidate_service.generate_candidates(
                user_id=user_id,
                target_date=target_date,
                profile=profile,
                weather=weather,
                scores=scores,
            )
        )

        lifestyle_ai = self._analyze_lifestyle(
            db=db,
            user_id=user_id,
            input_data={
                "user_id": str(user_id),
                "date": target_date,
                "profile": profile,
                "scores": scores,
                "weather": weather,
            },
        )
        copy_ai = self._generate_daily_plan_copy(
            db=db,
            user_id=user_id,
            input_data={
                "user_id": str(user_id),
                "date": target_date,
                "lifestyle_analysis": lifestyle_ai.model_dump(),
                "candidate_actions": [candidate.model_dump() for candidate in candidates],
            },
        )

        action_copy_by_id = {action.candidate_id: action for action in copy_ai.actions}
        total_saving_krw = sum(candidate.estimated_saving_krw for candidate in candidates)
        total_energy_saving_kwh = sum(candidate.estimated_energy_saving_kwh for candidate in candidates)
        total_co2_reduction_kg = sum(candidate.estimated_co2_reduction_kg for candidate in candidates)

        lifestyle_analysis = LifestyleAnalysis(
            user_id=user_id,
            date=target_date,
            primary_type=lifestyle_ai.primary_type,
            secondary_type=lifestyle_ai.secondary_type,
            confidence=Decimal(str(lifestyle_ai.confidence)),
            summary=lifestyle_ai.summary,
            reason=lifestyle_ai.reason,
            model_name=self.ai_client.model_name,
            prompt_version=self.ai_client.prompt_version,
            raw_ai_response=lifestyle_ai.model_dump(),
        )
        plan = RecommendationPlan(
            user_id=user_id,
            date=target_date,
            status="fallback" if isinstance(self.ai_client, FallbackAIClient) else "generated",
            total_estimated_saving_krw=total_saving_krw,
            monthly_estimated_saving_krw=total_saving_krw * 30,
            total_energy_saving_kwh=Decimal(str(round(total_energy_saving_kwh, 3))),
            total_co2_reduction_kg=Decimal(str(round(total_co2_reduction_kg, 3))),
            cheer_message=copy_ai.cheer_message,
            generated_by="fallback" if isinstance(self.ai_client, FallbackAIClient) else "ai",
        )
        actions = [
            self._build_action(
                user_id=user_id,
                target_date=target_date,
                candidate=candidate,
                action_copy=action_copy_by_id[candidate.candidate_id],
                sort_order=index,
            )
            for index, candidate in enumerate(candidates, start=1)
        ]

        saved_plan = self.recommendation_repository.create_daily_plan(
            db,
            lifestyle_analysis=lifestyle_analysis,
            plan=plan,
            actions=actions,
        )
        db.commit()
        return self.build_daily_plan_response(saved_plan), True

    def get_daily_plan(self, db: Session, *, user_id: UUID, target_date: Optional[dt.date]) -> DailyPlanResponse:
        resolved_date = target_date or today_kst()
        plan = self.recommendation_repository.get_daily_plan(db, user_id, resolved_date)
        if plan is None:
            raise ApiException(status_code=404, code="RECOMMENDATION_NOT_FOUND", message="추천 플랜을 찾을 수 없습니다.")
        return self.build_daily_plan_response(plan)

    def toggle_action(
        self,
        db: Session,
        *,
        user_id: UUID,
        action_id: UUID,
        request_data: ToggleActionRequest,
    ) -> ToggleActionResponse:
        action = self.recommendation_repository.get_action_for_user(db, action_id, user_id)
        if action is None:
            raise ApiException(status_code=404, code="RECOMMENDATION_NOT_FOUND", message="추천 행동을 찾을 수 없습니다.")

        previous_completed = action.is_completed
        target_completed = request_data.is_completed
        state_changed = previous_completed != target_completed
        delta = self._delta_for_action(action, target_completed) if state_changed else (0, 0.0, 0.0)

        if state_changed:
            if target_completed:
                action.is_completed = True
                action.completed_at = now_kst()
                event_type = "completed"
            else:
                action.is_completed = False
                action.completed_at = None
                event_type = "uncompleted"

            self.recommendation_repository.add_completion_log(
                db,
                ActionCompletionLog(
                    action_id=action.id,
                    user_id=user_id,
                    event_type=event_type,
                    saving_krw_delta=delta[0],
                    energy_kwh_delta=Decimal(str(delta[1])),
                    co2_kg_delta=Decimal(str(delta[2])),
                ),
            )

        try:
            db.commit()
        except Exception:
            rollback = getattr(db, "rollback", None)
            if callable(rollback):
                rollback()
            raise

        progress = self._build_today_progress(action.plan)
        return ToggleActionResponse(
            action_id=action.id,
            is_completed=action.is_completed,
            completed_at=action.completed_at,
            delta=ToggleActionDeltaResponse(
                saving_krw=delta[0],
                energy_saving_kwh=delta[1],
                co2_reduction_kg=delta[2],
            ),
            today_progress=progress,
        )

    def build_daily_plan_response(self, plan: RecommendationPlan) -> DailyPlanResponse:
        actions = sorted(plan.actions, key=lambda action: action.sort_order)
        return DailyPlanResponse(
            plan_id=plan.id,
            date=plan.date,
            lifestyle_analysis=LifestyleAnalysisResponse(
                primary_type=plan.lifestyle_analysis.primary_type,
                secondary_type=plan.lifestyle_analysis.secondary_type,
                confidence=float(plan.lifestyle_analysis.confidence),
                summary=plan.lifestyle_analysis.summary,
            )
            if plan.lifestyle_analysis
            else None,
            daily_summary=DailySummaryResponse(
                total_estimated_saving_krw=plan.total_estimated_saving_krw,
                monthly_estimated_saving_krw=plan.monthly_estimated_saving_krw,
                total_energy_saving_kwh=float(plan.total_energy_saving_kwh),
                total_co2_reduction_kg=float(plan.total_co2_reduction_kg),
                cheer_message=plan.cheer_message,
            ),
            actions=[
                RecommendationActionResponse(
                    action_id=action.id,
                    time_range=action.time_range,
                    sort_order=action.sort_order,
                    action_type=action.action_type,
                    title=action.title,
                    action=action.action,
                    reason=action.reason,
                    estimated_saving_krw=action.estimated_saving_krw,
                    estimated_energy_saving_kwh=float(action.estimated_energy_saving_kwh),
                    estimated_co2_reduction_kg=float(action.estimated_co2_reduction_kg),
                    difficulty=action.difficulty,
                    is_completed=action.is_completed,
                )
                for action in actions
            ],
            status=plan.status,
        )

    def _analyze_lifestyle(self, *, db: Session, user_id: UUID, input_data: Dict[str, Any]):
        start = time.perf_counter()
        try:
            response = self.ai_client.analyze_lifestyle(input_data)
            self._record_ai_log(db, user_id, "lifestyle_analysis", input_data, response.model_dump(), True, start)
            return response
        except Exception as exc:
            fallback_client = FallbackAIClient()
            response = fallback_client.analyze_lifestyle(input_data)
            self._record_ai_log(db, user_id, "lifestyle_analysis", input_data, response.model_dump(), False, start, "AI_GENERATION_FAILED")
            return response

    def _generate_daily_plan_copy(self, *, db: Session, user_id: UUID, input_data: Dict[str, Any]):
        start = time.perf_counter()
        try:
            response = self.ai_client.generate_daily_plan_copy(input_data)
            self._record_ai_log(db, user_id, "daily_plan", input_data, response.model_dump(), True, start)
            return response
        except Exception:
            fallback_client = FallbackAIClient()
            response = fallback_client.generate_daily_plan_copy(input_data)
            self._record_ai_log(db, user_id, "daily_plan", input_data, response.model_dump(), False, start, "AI_GENERATION_FAILED")
            return response

    def _record_ai_log(
        self,
        db: Session,
        user_id: UUID,
        request_type: str,
        request_payload: Dict[str, Any],
        response_payload: Dict[str, Any],
        success: bool,
        start: float,
        error_code: Optional[str] = None,
    ) -> None:
        record_ai_generation_log(
            db,
            user_id=user_id,
            request_type=request_type,
            prompt_version=self.ai_client.prompt_version,
            model_name=self.ai_client.model_name,
            success=success,
            latency_ms=int((time.perf_counter() - start) * 1000),
            error_code=error_code,
            request_payload=request_payload,
            response_payload=response_payload,
            commit=False,
        )

    def _build_action(
        self,
        *,
        user_id: UUID,
        target_date: dt.date,
        candidate: RecommendationCandidate,
        action_copy: DailyPlanActionCopyAIResponse,
        sort_order: int,
    ) -> RecommendationAction:
        return RecommendationAction(
            user_id=user_id,
            date=target_date,
            time_range=candidate.time_range,
            sort_order=sort_order,
            action_type=candidate.action_type,
            title=action_copy.title,
            action=action_copy.action,
            reason=action_copy.reason,
            estimated_saving_krw=candidate.estimated_saving_krw,
            estimated_energy_saving_kwh=Decimal(str(candidate.estimated_energy_saving_kwh)),
            estimated_co2_reduction_kg=Decimal(str(candidate.estimated_co2_reduction_kg)),
            difficulty=candidate.difficulty,
            priority_score=Decimal(str(candidate.priority_score)),
            is_completed=False,
        )

    def _build_today_progress(self, plan: RecommendationPlan) -> TodayProgressResponse:
        actions = list(plan.actions)
        completed_actions = [action for action in actions if action.is_completed]
        completed_saving_krw = sum(action.estimated_saving_krw for action in completed_actions)
        today_estimated_saving_krw = sum(action.estimated_saving_krw for action in actions)
        goal_achievement_rate = round((completed_saving_krw / today_estimated_saving_krw) * 100, 1) if today_estimated_saving_krw else 0.0

        return TodayProgressResponse(
            completed_action_count=len(completed_actions),
            total_action_count=len(actions),
            completed_saving_krw=completed_saving_krw,
            today_estimated_saving_krw=today_estimated_saving_krw,
            goal_achievement_rate=goal_achievement_rate,
            message=f"좋아요! 지금까지 약 {completed_saving_krw:,}원을 아꼈어요. 오늘 목표의 {goal_achievement_rate:g}%를 달성했습니다.",
        )

    def _delta_for_action(self, action: RecommendationAction, target_completed: bool) -> Tuple[int, float, float]:
        sign = 1 if target_completed else -1
        return (
            action.estimated_saving_krw * sign,
            float(action.estimated_energy_saving_kwh) * sign,
            float(action.estimated_co2_reduction_kg) * sign,
        )


def sort_candidates_by_priority(candidates: List[RecommendationCandidate]) -> List[RecommendationCandidate]:
    return sorted(candidates, key=lambda candidate: (-candidate.priority_score, candidate.action_type))
