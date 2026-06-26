from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field


class RecommendationCandidate(BaseModel):
    candidate_id: str
    time_range: str
    action_type: str
    estimated_saving_krw: int
    estimated_energy_saving_kwh: float
    estimated_co2_reduction_kg: float
    difficulty: str
    priority_score: float
    evidence: List[str] = Field(default_factory=list)


class RecommendationCandidateService:
    def generate_candidates(
        self,
        *,
        user_id: UUID,
        target_date: dt.date,
        profile: Dict[str, Any],
        weather: Dict[str, Any],
        scores: Dict[str, int],
    ) -> List[RecommendationCandidate]:
        home = profile.get("home_environment", {})
        lifestyle = profile.get("lifestyle", {})
        energy = profile.get("energy_profile", {})

        evidence_base = [
            _truthy_label(home.get("direction")),
            _truthy_label(home.get("window_size")),
            _truthy_label(home.get("floor_level")),
            _truthy_label(lifestyle.get("main_activity_time")),
            _truthy_label(energy.get("comfort_preference")),
        ]
        evidence = [item for item in evidence_base if item]

        return [
            RecommendationCandidate(
                candidate_id="cand_morning_ventilation",
                time_range="06:00~09:00",
                action_type="morning_ventilation",
                estimated_saving_krw=120,
                estimated_energy_saving_kwh=0.24,
                estimated_co2_reduction_kg=0.115,
                difficulty="쉬움",
                priority_score=_priority(scores, "cooling_need_score", 72),
                evidence=evidence + ["아침 시간대"],
            ),
            RecommendationCandidate(
                candidate_id="cand_pre_shading",
                time_range="10:00~12:00",
                action_type="pre_shading",
                estimated_saving_krw=130,
                estimated_energy_saving_kwh=0.26,
                estimated_co2_reduction_kg=0.124,
                difficulty="쉬움",
                priority_score=_priority(scores, "cooling_need_score", 76),
                evidence=evidence + ["낮 시간 햇빛"],
            ),
            RecommendationCandidate(
                candidate_id="cand_shading_before_outing",
                time_range="외출 전",
                action_type="shading_before_outing",
                estimated_saving_krw=150,
                estimated_energy_saving_kwh=0.30,
                estimated_co2_reduction_kg=0.143,
                difficulty="쉬움",
                priority_score=_priority(scores, "outing_score", 80),
                evidence=evidence + ["외출 전 차광"],
            ),
            RecommendationCandidate(
                candidate_id="cand_ac_temp_up",
                time_range="냉방 시작 시",
                action_type="ac_temp_up",
                estimated_saving_krw=210,
                estimated_energy_saving_kwh=0.42,
                estimated_co2_reduction_kg=0.201,
                difficulty="보통",
                priority_score=_priority(scores, "saving_priority_score", 84),
                evidence=evidence + ["설정온도 조정"],
            ),
            RecommendationCandidate(
                candidate_id="cand_fan_with_ac",
                time_range="냉방 중",
                action_type="fan_with_ac",
                estimated_saving_krw=90,
                estimated_energy_saving_kwh=0.18,
                estimated_co2_reduction_kg=0.086,
                difficulty="쉬움",
                priority_score=_priority(scores, "cooling_need_score", 68),
                evidence=evidence + ["공기 순환"],
            ),
            RecommendationCandidate(
                candidate_id="cand_timer_sleep",
                time_range="취침 전",
                action_type="timer_sleep",
                estimated_saving_krw=160,
                estimated_energy_saving_kwh=0.32,
                estimated_co2_reduction_kg=0.153,
                difficulty="쉬움",
                priority_score=_priority(scores, "night_score", 78),
                evidence=evidence + ["취침 전 타이머"],
            ),
            RecommendationCandidate(
                candidate_id="cand_close_window_check",
                time_range="냉방 전",
                action_type="close_window_check",
                estimated_saving_krw=70,
                estimated_energy_saving_kwh=0.14,
                estimated_co2_reduction_kg=0.067,
                difficulty="쉬움",
                priority_score=_priority(scores, "cooling_need_score", 65),
                evidence=evidence + ["창문 밀폐"],
            ),
            RecommendationCandidate(
                candidate_id="cand_safety_cooling",
                time_range="폭염 시간대",
                action_type="safety_cooling",
                estimated_saving_krw=0,
                estimated_energy_saving_kwh=0.0,
                estimated_co2_reduction_kg=0.0,
                difficulty="쉬움",
                priority_score=100.0 if _has_heat_alert(weather) else 50.0,
                evidence=evidence + ["안전 냉방"],
            ),
        ]


def _priority(scores: Dict[str, int], key: str, default: float) -> float:
    return float(scores.get(key, default) or default)


def _truthy_label(value: Any) -> str:
    return str(value) if value else ""


def _has_heat_alert(weather: Dict[str, Any]) -> bool:
    return any(block.get("heat_alert") for block in weather.get("time_blocks", []))
