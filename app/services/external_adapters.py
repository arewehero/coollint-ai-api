from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional
from uuid import UUID


class MockWeatherAdapter:
    """Temporary weather adapter until the weather service is available."""

    def get_daily_weather(
        self,
        *,
        user_id: UUID,
        target_date: dt.date,
        location: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "date": target_date,
            "provider": "mock",
            "location": location or {},
            "time_blocks": [
                {"time_range": "06:00~09:00", "temperature": 25.5, "heat_alert": False},
                {"time_range": "12:00~15:00", "temperature": 31.0, "heat_alert": False},
                {"time_range": "18:00~21:00", "temperature": 28.0, "heat_alert": False},
            ],
        }


class MockScoringAdapter:
    """Temporary scoring adapter until scoring/calculation services are available."""

    def calculate_scores(self, *, profile: Dict[str, Any], weather: Dict[str, Any]) -> Dict[str, int]:
        lifestyle = profile.get("lifestyle", {})
        energy_profile = profile.get("energy_profile", {})

        main_activity_time = lifestyle.get("main_activity_time")
        daytime_home_stay = lifestyle.get("daytime_home_stay")
        comfort_preference = energy_profile.get("comfort_preference")

        return {
            "morning_score": 80 if main_activity_time == "아침형" else 45,
            "daytime_score": 75 if main_activity_time == "낮 활동" else 45,
            "night_score": 82 if main_activity_time == "야간 활동" else 45,
            "irregular_score": 78 if main_activity_time == "불규칙" else 35,
            "stay_home_score": 85 if daytime_home_stay in {"오후 오래", "종일 재택"} else 40,
            "outing_score": 80 if daytime_home_stay == "거의 없음" else 45,
            "cooling_need_score": 75,
            "saving_priority_score": 85 if comfort_preference == "절약 우선" else 60,
        }
