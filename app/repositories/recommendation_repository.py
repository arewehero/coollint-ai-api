from __future__ import annotations

import datetime as dt
from typing import Iterable, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import ActionCompletionLog, LifestyleAnalysis, RecommendationAction, RecommendationPlan
from app.models.score import ScoreSnapshot


class RecommendationRepository:
    def get_daily_plan(self, db: Session, user_id: UUID, target_date: dt.date) -> Optional[RecommendationPlan]:
        statement = (
            select(RecommendationPlan)
            .where(RecommendationPlan.user_id == user_id, RecommendationPlan.date == target_date)
            .options(
                selectinload(RecommendationPlan.actions),
                selectinload(RecommendationPlan.lifestyle_analysis),
            )
        )
        return db.execute(statement).scalars().first()

    def has_completed_actions(self, plan: RecommendationPlan) -> bool:
        return any(action.is_completed for action in plan.actions)

    def delete_plan(self, db: Session, plan: RecommendationPlan) -> None:
        db.delete(plan)
        db.flush()

    def create_daily_plan(
        self,
        db: Session,
        *,
        lifestyle_analysis: LifestyleAnalysis,
        plan: RecommendationPlan,
        actions: Iterable[RecommendationAction],
    ) -> RecommendationPlan:
        db.add(lifestyle_analysis)
        plan.lifestyle_analysis = lifestyle_analysis
        plan.actions = list(actions)
        db.add(plan)
        db.flush()
        return plan

    def get_lifestyle_analysis(self, db: Session, user_id: UUID, target_date: dt.date) -> Optional[LifestyleAnalysis]:
        """Retrieve the most recent LifestyleAnalysis for (user_id, date)."""
        statement = (
            select(LifestyleAnalysis)
            .where(LifestyleAnalysis.user_id == user_id, LifestyleAnalysis.date == target_date)
        )
        return db.execute(statement).scalars().first()

    def get_score_snapshot(self, db: Session, user_id: UUID, target_date: dt.date) -> Optional[ScoreSnapshot]:
        """Retrieve the ScoreSnapshot for (user_id, date)."""
        statement = (
            select(ScoreSnapshot)
            .where(ScoreSnapshot.user_id == user_id, ScoreSnapshot.date == target_date)
        )
        return db.execute(statement).scalars().first()

    def get_action_for_user(self, db: Session, action_id: UUID, user_id: UUID) -> Optional[RecommendationAction]:
        statement = (
            select(RecommendationAction)
            .where(RecommendationAction.id == action_id, RecommendationAction.user_id == user_id)
            .options(
                selectinload(RecommendationAction.plan).selectinload(RecommendationPlan.actions),
            )
        )
        return db.execute(statement).scalars().first()

    def add_completion_log(self, db: Session, log: ActionCompletionLog) -> None:
        db.add(log)

    def list_actions_for_period(
        self,
        db: Session,
        *,
        user_id: UUID,
        period_start: dt.date,
        period_end: dt.date,
    ) -> List[RecommendationAction]:
        statement = (
            select(RecommendationAction)
            .where(
                RecommendationAction.user_id == user_id,
                RecommendationAction.date >= period_start,
                RecommendationAction.date <= period_end,
            )
            .order_by(RecommendationAction.date, RecommendationAction.sort_order)
        )
        return list(db.execute(statement).scalars().all())

    def list_daily_plans_for_period(
        self,
        db: Session,
        *,
        user_id: UUID,
        period_start: dt.date,
        period_end: dt.date,
    ) -> List[RecommendationPlan]:
        statement = (
            select(RecommendationPlan)
            .where(
                RecommendationPlan.user_id == user_id,
                RecommendationPlan.date >= period_start,
                RecommendationPlan.date <= period_end,
            )
            .options(selectinload(RecommendationPlan.actions))
            .order_by(RecommendationPlan.date)
        )
        return list(db.execute(statement).scalars().all())
