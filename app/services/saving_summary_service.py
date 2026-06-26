from __future__ import annotations

import calendar
import datetime as dt
from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ApiException
from app.core.time import today_kst
from app.repositories.profile_repository import ProfileRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendation import (
    SavingsCalendarDayResponse,
    SavingsCalendarMonthlyTotalResponse,
    SavingsCalendarResponse,
    SavingsGoalResponse,
    SavingsSummaryResponse,
)


class SavingSummaryService:
    def __init__(
        self,
        *,
        profile_repository: ProfileRepository,
        recommendation_repository: RecommendationRepository,
    ) -> None:
        self.profile_repository = profile_repository
        self.recommendation_repository = recommendation_repository

    def get_summary(
        self,
        db: Session,
        *,
        user_id: UUID,
        period: str,
        reference_date: Optional[dt.date],
    ) -> SavingsSummaryResponse:
        resolved_date = reference_date or today_kst()
        period_start, period_end = calculate_period(period, resolved_date)
        actions = self.recommendation_repository.list_actions_for_period(
            db,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )
        totals = aggregate_actions(actions)
        monthly_projected = project_monthly_saving(
            total_saving_krw=totals["total_saving_krw"],
            period_start=period_start,
            period_end=period_end,
            reference_date=resolved_date,
        )
        profile = self.profile_repository.get_profile(db, user_id)
        goal = build_goal(profile, monthly_projected)

        return SavingsSummaryResponse(
            period=period,
            period_start=period_start,
            period_end=period_end,
            completed_action_count=totals["completed_action_count"],
            total_action_count=totals["total_action_count"],
            total_saving_krw=totals["total_saving_krw"],
            total_possible_saving_krw=totals["total_possible_saving_krw"],
            total_energy_saving_kwh=totals["total_energy_saving_kwh"],
            total_possible_energy_saving_kwh=totals["total_possible_energy_saving_kwh"],
            total_co2_reduction_kg=totals["total_co2_reduction_kg"],
            total_possible_co2_reduction_kg=totals["total_possible_co2_reduction_kg"],
            monthly_projected_saving_krw=monthly_projected,
            goal=goal,
            message=build_summary_message(goal, monthly_projected, totals["total_saving_krw"]),
        )

    def get_calendar(self, db: Session, *, user_id: UUID, month: str) -> SavingsCalendarResponse:
        period_start, period_end = parse_month_period(month)
        actions = self.recommendation_repository.list_actions_for_period(
            db,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )
        grouped: DefaultDict[dt.date, List] = defaultdict(list)
        for action in actions:
            grouped[action.date].append(action)

        days = []
        current = period_start
        while current <= period_end:
            totals = aggregate_actions(grouped[current])
            days.append(
                SavingsCalendarDayResponse(
                    date=current,
                    completed_action_count=totals["completed_action_count"],
                    total_saving_krw=totals["total_saving_krw"],
                    total_co2_reduction_kg=totals["total_co2_reduction_kg"],
                )
            )
            current += dt.timedelta(days=1)

        monthly_totals = aggregate_actions(actions)
        return SavingsCalendarResponse(
            month=month,
            days=days,
            monthly_total=SavingsCalendarMonthlyTotalResponse(
                saving_krw=monthly_totals["total_saving_krw"],
                energy_saving_kwh=monthly_totals["total_energy_saving_kwh"],
                co2_reduction_kg=monthly_totals["total_co2_reduction_kg"],
            ),
        )


def calculate_period(period: str, reference_date: dt.date) -> Tuple[dt.date, dt.date]:
    if period == "today":
        return reference_date, reference_date
    if period == "week":
        start = reference_date - dt.timedelta(days=reference_date.weekday())
        return start, start + dt.timedelta(days=6)
    if period == "month":
        _, last_day = calendar.monthrange(reference_date.year, reference_date.month)
        return reference_date.replace(day=1), reference_date.replace(day=last_day)
    raise ApiException(status_code=400, code="INVALID_PERIOD", message="period 파라미터는 today, week, month 중 하나여야 합니다.")


def parse_month_period(month: str) -> Tuple[dt.date, dt.date]:
    try:
        year_text, month_text = month.split("-", 1)
        year = int(year_text)
        month_number = int(month_text)
        _, last_day = calendar.monthrange(year, month_number)
    except ValueError as exc:
        raise ApiException(status_code=400, code="INVALID_PROFILE_INPUT", message="month는 YYYY-MM 형식이어야 합니다.") from exc
    return dt.date(year, month_number, 1), dt.date(year, month_number, last_day)


def aggregate_actions(actions: Iterable) -> Dict[str, float]:
    action_list = list(actions)
    completed_actions = [action for action in action_list if action.is_completed]
    return {
        "completed_action_count": len(completed_actions),
        "total_action_count": len(action_list),
        "total_saving_krw": sum(action.estimated_saving_krw for action in completed_actions),
        "total_possible_saving_krw": sum(action.estimated_saving_krw for action in action_list),
        "total_energy_saving_kwh": round(sum(float(action.estimated_energy_saving_kwh) for action in completed_actions), 3),
        "total_possible_energy_saving_kwh": round(sum(float(action.estimated_energy_saving_kwh) for action in action_list), 3),
        "total_co2_reduction_kg": round(sum(float(action.estimated_co2_reduction_kg) for action in completed_actions), 3),
        "total_possible_co2_reduction_kg": round(sum(float(action.estimated_co2_reduction_kg) for action in action_list), 3),
    }


def project_monthly_saving(
    *,
    total_saving_krw: int,
    period_start: dt.date,
    period_end: dt.date,
    reference_date: dt.date,
) -> int:
    _, days_in_month = calendar.monthrange(reference_date.year, reference_date.month)
    elapsed_end = min(max(reference_date, period_start), period_end)
    elapsed_days = max((elapsed_end - period_start).days + 1, 1)
    return round(total_saving_krw / elapsed_days * days_in_month)


def build_goal(profile: Optional[Dict], monthly_projected_saving_krw: int) -> Optional[SavingsGoalResponse]:
    if not profile:
        return None

    energy_profile = profile.get("energy_profile", {})
    monthly_electricity_bill = energy_profile.get("monthly_electricity_bill")
    if monthly_electricity_bill is None:
        return None

    monthly_goal_bill = energy_profile.get("monthly_goal_bill")
    required_monthly_saving = max(monthly_electricity_bill - monthly_goal_bill, 0) if monthly_goal_bill is not None else None
    on_track = monthly_projected_saving_krw >= required_monthly_saving if required_monthly_saving is not None else False

    return SavingsGoalResponse(
        monthly_electricity_bill=monthly_electricity_bill,
        monthly_goal_bill=monthly_goal_bill,
        required_monthly_saving_krw=required_monthly_saving,
        current_projected_saving_krw=monthly_projected_saving_krw,
        on_track=on_track,
    )


def build_summary_message(goal: Optional[SavingsGoalResponse], monthly_projected_saving_krw: int, total_saving_krw: int) -> str:
    if goal and goal.required_monthly_saving_krw is not None:
        gap = monthly_projected_saving_krw - goal.required_monthly_saving_krw
        if gap >= 0:
            return f"현재 페이스면 이번 달 목표보다 약 {gap:,}원 더 아낄 수 있어요."
        return f"현재 페이스면 이번 달 목표까지 약 {abs(gap):,}원이 더 필요해요."
    return f"지금까지 약 {total_saving_krw:,}원을 아꼈어요. 작은 실천을 계속 이어가 보세요."
