from __future__ import annotations

import datetime as dt
import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ApiException, ErrorCode
from app.core.time import now_kst, today_kst
from app.models import ActionCompletionLog, LifestyleAnalysis, RecommendationAction, RecommendationPlan
from app.models.score import ScoreSnapshot
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

logger = logging.getLogger(__name__)


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
        """Create or return an existing daily recommendation plan.

        Full orchestration flow:
        1. Check existing plan for user_id + date → if exists and !force_regenerate, return existing
        2. If force_regenerate, delete existing plan
        3. Validate: LifestyleAnalysis + ScoreSnapshot must exist → 422 PREREQUISITE_MISSING if not
        4. Get weather data for date
        5. Build candidates via CandidateService (kWh/KRW/CO₂ calculated inside)
        6. Call AI for text copy (title, action, reason, cheer_message) → 8s timeout
        7. If AI fails → use fallback template, set status="fallback"
        8. Create RecommendationPlan + RecommendationActions in DB
        9. Calculate daily_summary (total savings, monthly projection, energy, CO₂)
        10. Return DailyPlanResponse with cheer_message

        Requirements: 6.1, 6.2, 6.3, 6.4, 6.7, 6.8, 6.10
        """
        target_date = request_data.date or today_kst()

        # ---------------------------------------------------------------
        # Step 1: Check existing plan (Req 6.1)
        # ---------------------------------------------------------------
        existing_plan = self.recommendation_repository.get_daily_plan(db, user_id, target_date)
        if existing_plan and not request_data.force_regenerate:
            return self.build_daily_plan_response(existing_plan), False

        # ---------------------------------------------------------------
        # Step 2: Force regenerate → delete existing plan (Req 6.2)
        # ---------------------------------------------------------------
        if existing_plan and request_data.force_regenerate:
            if self.recommendation_repository.has_completed_actions(existing_plan):
                raise ApiException(
                    status_code=409,
                    code="ACTION_ALREADY_COMPLETED",
                    message="이미 완료된 행동이 있어 추천 플랜을 재생성할 수 없습니다.",
                )
            self.recommendation_repository.delete_plan(db, existing_plan)

        # ---------------------------------------------------------------
        # Step 3: Validate prerequisites (Req 6.10)
        # LifestyleAnalysis + ScoreSnapshot must exist
        # ---------------------------------------------------------------
        lifestyle_analysis_record = self.recommendation_repository.get_lifestyle_analysis(db, user_id, target_date)
        score_snapshot = self.recommendation_repository.get_score_snapshot(db, user_id, target_date)

        missing: List[str] = []
        if lifestyle_analysis_record is None:
            missing.append("LifestyleAnalysis")
        if score_snapshot is None:
            missing.append("ScoreSnapshot")

        if missing:
            raise ApiException.from_error_code(
                ErrorCode.PREREQUISITE_MISSING,
                message=f"선행 데이터가 존재하지 않습니다: {', '.join(missing)}. 먼저 점수 계산과 생활유형 분석을 수행해주세요.",
                details={"missing": missing},
            )

        # ---------------------------------------------------------------
        # Step 4: Get weather data
        # ---------------------------------------------------------------
        location = request_data.location.model_dump(exclude_none=True) if request_data.location else {}
        weather = self.weather_adapter.get_daily_weather(user_id=user_id, target_date=target_date, location=location)

        # ---------------------------------------------------------------
        # Step 5: Build candidates with CalculationEngine (Req 6.3, 6.4)
        # Use ScoreSnapshot scores for candidate generation
        # ---------------------------------------------------------------
        scores_dict = self._score_snapshot_to_dict(score_snapshot)
        profile = self.profile_repository.get_profile(db, user_id)
        if profile is None:
            raise ApiException(status_code=404, code="PROFILE_NOT_FOUND", message="사용자 프로필을 찾을 수 없습니다.")

        candidates = sort_candidates_by_priority(
            self.candidate_service.generate_candidates(
                user_id=user_id,
                target_date=target_date,
                profile=profile,
                weather=weather,
                scores=scores_dict,
            )
        )

        # ---------------------------------------------------------------
        # Step 6 & 7: Call AI for copy text → fallback on failure (Req 6.8, 6.9)
        # ---------------------------------------------------------------
        used_fallback = False
        copy_ai = self._generate_daily_plan_copy(
            db=db,
            user_id=user_id,
            input_data={
                "user_id": str(user_id),
                "date": str(target_date),
                "lifestyle_analysis": {
                    "primary_type": lifestyle_analysis_record.primary_type,
                    "secondary_type": lifestyle_analysis_record.secondary_type,
                    "confidence": float(lifestyle_analysis_record.confidence),
                    "summary": lifestyle_analysis_record.summary,
                    "reason": getattr(lifestyle_analysis_record, "reason", None) or "",
                },
                "candidate_actions": [candidate.model_dump() for candidate in candidates],
            },
        )
        # Check if fallback was used (tracked via _generate_daily_plan_copy internal logic)
        if hasattr(copy_ai, "_used_fallback"):
            used_fallback = copy_ai._used_fallback
        # Also detect fallback from the method's exception handling
        used_fallback = getattr(self, "_last_copy_used_fallback", False)

        # ---------------------------------------------------------------
        # Step 8 & 9: Calculate daily_summary and create plan (Req 6.4, 6.7)
        # kWh/KRW/CO₂ already calculated in CandidateService
        # ---------------------------------------------------------------
        action_copy_by_id = {action.candidate_id: action for action in copy_ai.actions}
        total_saving_krw = sum(candidate.estimated_saving_krw for candidate in candidates)
        total_energy_saving_kwh = sum(candidate.estimated_energy_saving_kwh for candidate in candidates)
        total_co2_reduction_kg = sum(candidate.estimated_co2_reduction_kg for candidate in candidates)

        # Monthly projection (Req 6.7): daily total × 30
        monthly_estimated_saving_krw = total_saving_krw * 30

        # Determine plan status
        plan_status = "fallback" if used_fallback else "generated"
        generated_by = "fallback" if used_fallback else "ai"

        plan = RecommendationPlan(
            user_id=user_id,
            date=target_date,
            lifestyle_analysis_id=lifestyle_analysis_record.id,
            status=plan_status,
            total_estimated_saving_krw=total_saving_krw,
            monthly_estimated_saving_krw=monthly_estimated_saving_krw,
            total_energy_saving_kwh=Decimal(str(round(total_energy_saving_kwh, 3))),
            total_co2_reduction_kg=Decimal(str(round(total_co2_reduction_kg, 3))),
            cheer_message=copy_ai.cheer_message,
            generated_by=generated_by,
        )
        actions = [
            self._build_action(
                user_id=user_id,
                target_date=target_date,
                candidate=candidate,
                action_copy=action_copy_by_id.get(candidate.candidate_id),
                sort_order=index,
            )
            for index, candidate in enumerate(candidates, start=1)
        ]

        # Save plan with relationship to existing LifestyleAnalysis
        plan.lifestyle_analysis_id = lifestyle_analysis_record.id
        saved_plan = self.recommendation_repository.create_daily_plan(
            db,
            lifestyle_analysis=lifestyle_analysis_record,
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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _score_snapshot_to_dict(self, snapshot: ScoreSnapshot) -> Dict[str, int]:
        """Convert a ScoreSnapshot ORM object to a dict of score fields."""
        return {
            "morning_score": snapshot.morning_score,
            "daytime_score": snapshot.daytime_score,
            "night_score": snapshot.night_score,
            "irregular_score": snapshot.irregular_score,
            "stay_home_score": snapshot.stay_home_score,
            "outing_score": snapshot.outing_score,
            "cooling_need_score": snapshot.cooling_need_score,
            "saving_priority_score": snapshot.saving_priority_score,
            "saving_opportunity_score": snapshot.saving_opportunity_score,
            "heat_gain_score": snapshot.heat_gain_score,
            "cooling_loss_score": snapshot.cooling_loss_score,
            "ventilation_score": snapshot.ventilation_score,
        }

    def _generate_daily_plan_copy(self, *, db: Session, user_id: UUID, input_data: Dict[str, Any]):
        """Call AI client for recommendation copy text. Falls back on failure (Req 6.8)."""
        self._last_copy_used_fallback = False
        start = time.perf_counter()
        try:
            response = self.ai_client.generate_daily_plan_copy(input_data)
            self._record_ai_log(db, user_id, "daily_plan", input_data, response.model_dump(), True, start)
            return response
        except Exception as exc:
            logger.warning("AI daily plan copy generation failed, using fallback: %s", exc)
            self._last_copy_used_fallback = True
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
        action_copy: Optional[DailyPlanActionCopyAIResponse],
        sort_order: int,
    ) -> RecommendationAction:
        """Build a RecommendationAction from candidate + AI copy text."""
        # If action_copy is not available (e.g. candidate_id mismatch), use defaults
        title = action_copy.title if action_copy else candidate.action_type
        action_text = action_copy.action if action_copy else "추천 행동을 실천해보세요."
        reason_text = action_copy.reason if action_copy else "생활패턴과 날씨 조건을 바탕으로 추천된 행동입니다."

        return RecommendationAction(
            user_id=user_id,
            date=target_date,
            time_range=candidate.time_range,
            sort_order=sort_order,
            action_type=candidate.action_type,
            title=title,
            action=action_text,
            reason=reason_text,
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
