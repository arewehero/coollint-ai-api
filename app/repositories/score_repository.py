"""Score snapshot repository with upsert and query operations.

Requirements: 4.3, 4.6
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.score import ScoreSnapshot


class ScoreRepository:
    """Repository for ScoreSnapshot domain: upsert and query operations."""

    def upsert_score_snapshot(
        self,
        db: Session,
        user_id: UUID,
        date: dt.date,
        scores_dict: Dict[str, Any],
    ) -> ScoreSnapshot:
        """Insert or update a ScoreSnapshot for (user_id, date).

        If a snapshot already exists for the same user_id and date,
        it will be updated with the new scores (Req 4.6 upsert).
        Otherwise, a new record is created.

        Args:
            db: Database session.
            user_id: The user's UUID.
            date: The target date.
            scores_dict: Dict with 12 score fields + dominant_signals.

        Returns:
            The created or updated ScoreSnapshot ORM instance.
        """
        existing = (
            db.query(ScoreSnapshot)
            .filter(ScoreSnapshot.user_id == user_id, ScoreSnapshot.date == date)
            .first()
        )

        # Extract the 12 score fields and raw_scores
        score_fields = [
            "morning_score",
            "daytime_score",
            "night_score",
            "irregular_score",
            "stay_home_score",
            "outing_score",
            "cooling_need_score",
            "saving_priority_score",
            "saving_opportunity_score",
            "heat_gain_score",
            "cooling_loss_score",
            "ventilation_score",
        ]

        if existing:
            for field in score_fields:
                if field in scores_dict:
                    setattr(existing, field, scores_dict[field])
            # Store the full scores dict as raw_scores for traceability
            existing.raw_scores = scores_dict
            db.flush()
            return existing

        # Build new record
        record_data = {field: scores_dict[field] for field in score_fields}
        record_data["raw_scores"] = scores_dict
        record = ScoreSnapshot(user_id=user_id, date=date, **record_data)
        db.add(record)
        db.flush()
        return record

    def get_score_snapshot(
        self,
        db: Session,
        user_id: UUID,
        date: dt.date,
    ) -> Optional[ScoreSnapshot]:
        """Retrieve a ScoreSnapshot for (user_id, date).

        Args:
            db: Database session.
            user_id: The user's UUID.
            date: The target date.

        Returns:
            ScoreSnapshot instance or None if not found.
        """
        return (
            db.query(ScoreSnapshot)
            .filter(ScoreSnapshot.user_id == user_id, ScoreSnapshot.date == date)
            .first()
        )
