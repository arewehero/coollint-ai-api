from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


class ProfileRepository:
    """Adapter for the shared profile domain owned by another backend part."""

    def get_profile(self, db: Session, user_id: UUID) -> Optional[Dict[str, Any]]:
        bind = db.get_bind()
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
        bind = db.get_bind()
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
