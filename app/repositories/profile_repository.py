"""Profile repository with upsert operations for home_environments, lifestyle_inputs, user_profiles.

Requirements: 2.1, 2.5, 2.6, 2.7
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.profile import HomeEnvironment, LifestyleInput, UserProfile
from app.schemas.profile import EnergyProfileSchema, HomeEnvironmentSchema, LifestyleSchema


class ProfileRepository:
    """Repository for profile domain: upsert and query operations."""

    # ------------------------------------------------------------------
    # Upsert operations
    # ------------------------------------------------------------------

    def upsert_home_environment(
        self, db: Session, user_id: UUID, data: HomeEnvironmentSchema
    ) -> HomeEnvironment:
        """Insert or update home_environment for user_id."""
        existing = (
            db.query(HomeEnvironment)
            .filter(HomeEnvironment.user_id == user_id)
            .first()
        )
        if existing:
            for field, value in data.model_dump().items():
                setattr(existing, field, value)
            db.flush()
            return existing

        record = HomeEnvironment(user_id=user_id, **data.model_dump())
        db.add(record)
        db.flush()
        return record

    def upsert_lifestyle_input(
        self, db: Session, user_id: UUID, data: LifestyleSchema
    ) -> LifestyleInput:
        """Insert or update lifestyle_input for user_id."""
        existing = (
            db.query(LifestyleInput)
            .filter(LifestyleInput.user_id == user_id)
            .first()
        )
        if existing:
            for field, value in data.model_dump().items():
                setattr(existing, field, value)
            db.flush()
            return existing

        record = LifestyleInput(user_id=user_id, **data.model_dump())
        db.add(record)
        db.flush()
        return record

    def upsert_energy_profile(
        self, db: Session, user_id: UUID, data: EnergyProfileSchema
    ) -> UserProfile:
        """Insert or update user_profile (energy profile) for user_id."""
        existing = (
            db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )
        if existing:
            for field, value in data.model_dump().items():
                setattr(existing, field, value)
            db.flush()
            return existing

        record = UserProfile(user_id=user_id, **data.model_dump())
        db.add(record)
        db.flush()
        return record

    def get_full_profile(
        self, db: Session, user_id: UUID
    ) -> Optional[Tuple[HomeEnvironment, LifestyleInput, UserProfile]]:
        """Retrieve all 3 profile records for a user. Returns None if any is missing."""
        home = (
            db.query(HomeEnvironment)
            .filter(HomeEnvironment.user_id == user_id)
            .first()
        )
        lifestyle = (
            db.query(LifestyleInput)
            .filter(LifestyleInput.user_id == user_id)
            .first()
        )
        energy = (
            db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )

        if not home or not lifestyle or not energy:
            return None

        return (home, lifestyle, energy)

    # ------------------------------------------------------------------
    # Legacy methods (kept for backward compatibility with existing services)
    # ------------------------------------------------------------------

    def get_profile(self, db: Session, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get profile as dict (used by recommendation and scoring services)."""
        result = self.get_full_profile(db, user_id)
        if result is None:
            # Fallback to raw SQL for cases where ORM tables might not be mapped
            return self._get_profile_raw(db, user_id)

        home, lifestyle, energy = result
        return {
            "energy_profile": {
                "monthly_electricity_bill": energy.monthly_electricity_bill,
                "monthly_goal_bill": energy.monthly_goal_bill,
                "comfort_preference": energy.comfort_preference,
                "ac_type": energy.ac_type,
                "has_fan": energy.has_fan,
                "curtain_type": energy.curtain_type,
                "ac_power_watt": energy.ac_power_watt,
                "room_size": energy.room_size,
                "current_temperature_setting": (
                    float(energy.current_temperature_setting)
                    if energy.current_temperature_setting is not None
                    else None
                ),
                "daily_ac_usage_hours": (
                    float(energy.daily_ac_usage_hours)
                    if energy.daily_ac_usage_hours is not None
                    else None
                ),
                "electricity_unit_price": (
                    float(energy.electricity_unit_price)
                    if energy.electricity_unit_price is not None
                    else None
                ),
            },
            "home_environment": {
                "housing_type": home.housing_type,
                "direction": home.direction,
                "floor_level": home.floor_level,
                "building_age": home.building_age,
                "insulation_level": home.insulation_level,
                "window_size": home.window_size,
                "ventilation_level": home.ventilation_level,
                "window_sealing": home.window_sealing,
            },
            "lifestyle": {
                "main_activity_time": lifestyle.main_activity_time,
                "daytime_home_stay": lifestyle.daytime_home_stay,
                "sleep_time": lifestyle.sleep_time,
                "outdoor_activity": lifestyle.outdoor_activity,
                "hot_time_home_stay": lifestyle.hot_time_home_stay,
            },
        }

    def _get_profile_raw(self, db: Session, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Raw SQL fallback for get_profile (backward compatibility)."""
        try:
            bind = db.get_bind()
        except AttributeError:
            return None

        table_names = set(inspect(bind).get_table_names())
        required_tables = {"user_profiles", "home_environments", "lifestyle_inputs"}
        if not required_tables.issubset(table_names):
            return None

        profile = db.execute(
            text(
                """
                SELECT monthly_electricity_bill, monthly_goal_bill, comfort_preference,
                       ac_type, has_fan, curtain_type, ac_power_watt, room_size,
                       current_temperature_setting, daily_ac_usage_hours, electricity_unit_price
                FROM user_profiles
                WHERE user_id = :user_id
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().first()
        home_environment = db.execute(
            text(
                """
                SELECT housing_type, direction, floor_level, building_age, insulation_level,
                       window_size, ventilation_level, window_sealing
                FROM home_environments
                WHERE user_id = :user_id
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().first()
        lifestyle = db.execute(
            text(
                """
                SELECT main_activity_time, daytime_home_stay, sleep_time,
                       outdoor_activity, hot_time_home_stay
                FROM lifestyle_inputs
                WHERE user_id = :user_id
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().first()

        if not profile or not home_environment or not lifestyle:
            return None

        return {
            "energy_profile": dict(profile),
            "home_environment": dict(home_environment),
            "lifestyle": dict(lifestyle),
        }

    def list_active_user_ids_with_profiles(self, db: Session) -> List[UUID]:
        """List all active users with complete profiles."""
        try:
            bind = db.get_bind()
        except AttributeError:
            return []

        inspector = inspect(bind)
        table_names = set(inspector.get_table_names())
        required_tables = {"users", "user_profiles", "home_environments", "lifestyle_inputs"}
        if not required_tables.issubset(table_names):
            return []

        user_columns = {column["name"] for column in inspector.get_columns("users")}
        active_filter = "WHERE u.deleted_at IS NULL" if "deleted_at" in user_columns else ""
        rows = db.execute(
            text(
                f"""
                SELECT DISTINCT u.id
                FROM users u
                JOIN user_profiles up ON up.user_id = u.id
                JOIN home_environments he ON he.user_id = u.id
                JOIN lifestyle_inputs li ON li.user_id = u.id
                {active_filter}
                """
            )
        ).scalars().all()
        return [UUID(str(row)) for row in rows]
