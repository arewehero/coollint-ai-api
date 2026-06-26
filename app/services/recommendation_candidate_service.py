"""Recommendation Candidate Service.

Generates candidate actions for daily recommendation plans based on
user scores, weather conditions, and lifestyle type.

Key responsibilities:
- Build action candidates with calculated savings (CalculationService)
- Filter out AC-off actions during heatwave (>=35°C)
- Enforce min 3, max 10 candidates per plan
- Sort by priority_score descending
- Assign action_type, difficulty, priority_score

Requirements: 6.3, 6.5, 6.6
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.calculation_service import (
    DEFAULT_AC_POWER_WATT,
    DEFAULT_UNIT_PRICE,
    calculate_co2_reduction,
    calculate_energy_kwh,
    calculate_saving_krw,
    estimate_ac_power_watt,
    temperature_coefficient,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEATWAVE_THRESHOLD: float = 35.0
MIN_CANDIDATES: int = 3
MAX_CANDIDATES: int = 10

# Action types that involve turning off AC (excluded during heatwave)
AC_OFF_ACTION_TYPES: set[str] = {
    "ac_off",
    "에어컨_끄기",
    "에어컨_off",
    "ac_power_off",
}

# Time ranges as defined in design spec
TIME_RANGES: list[str] = ["새벽", "아침", "오전", "오후", "저녁", "밤"]

# Difficulty levels
DIFFICULTY_EASY = "쉬움"
DIFFICULTY_NORMAL = "보통"
DIFFICULTY_HARD = "약간 어려움"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class ActionCandidate(BaseModel):
    """A candidate action for recommendation plan generation."""

    candidate_id: str
    time_range: str
    sort_order: int = 0
    action_type: str
    difficulty: str
    priority_score: float = Field(ge=0, le=10)
    estimated_saving_krw: int = 0
    estimated_energy_saving_kwh: float = 0.0
    estimated_co2_reduction_kg: float = 0.0
    evidence: List[str] = Field(default_factory=list)


# Keep backward-compatible alias
RecommendationCandidate = ActionCandidate


# ---------------------------------------------------------------------------
# Action Templates
# ---------------------------------------------------------------------------


class _ActionTemplate:
    """Definition of a potential action with scoring/calculation parameters."""

    def __init__(
        self,
        *,
        action_type: str,
        time_range: str,
        difficulty: str,
        base_priority: float,
        score_key: str,
        score_weight: float = 0.3,
        usage_hours: float = 1.0,
        power_fraction: float = 1.0,
        evidence_label: str,
        is_ac_off: bool = False,
        requires_fan: bool = False,
        requires_ac: bool = False,
    ):
        self.action_type = action_type
        self.time_range = time_range
        self.difficulty = difficulty
        self.base_priority = base_priority
        self.score_key = score_key
        self.score_weight = score_weight
        self.usage_hours = usage_hours
        self.power_fraction = power_fraction
        self.evidence_label = evidence_label
        self.is_ac_off = is_ac_off
        self.requires_fan = requires_fan
        self.requires_ac = requires_ac


# All possible action templates
_ACTION_TEMPLATES: list[_ActionTemplate] = [
    _ActionTemplate(
        action_type="ventilation",
        time_range="아침",
        difficulty=DIFFICULTY_EASY,
        base_priority=6.0,
        score_key="ventilation_score",
        usage_hours=0.5,
        power_fraction=0.3,
        evidence_label="아침 환기로 실내 온도 낮추기",
    ),
    _ActionTemplate(
        action_type="shading",
        time_range="오전",
        difficulty=DIFFICULTY_EASY,
        base_priority=6.5,
        score_key="heat_gain_score",
        usage_hours=2.0,
        power_fraction=0.2,
        evidence_label="차광으로 실내 열유입 감소",
    ),
    _ActionTemplate(
        action_type="ac_temp_up",
        time_range="오후",
        difficulty=DIFFICULTY_NORMAL,
        base_priority=7.5,
        score_key="saving_priority_score",
        usage_hours=3.0,
        power_fraction=0.15,
        evidence_label="에어컨 온도 1°C 올려 에너지 절약",
        requires_ac=True,
    ),
    _ActionTemplate(
        action_type="fan_usage",
        time_range="오후",
        difficulty=DIFFICULTY_EASY,
        base_priority=5.5,
        score_key="cooling_need_score",
        usage_hours=2.0,
        power_fraction=0.05,
        evidence_label="선풍기 활용으로 체감 온도 낮추기",
        requires_fan=True,
    ),
    _ActionTemplate(
        action_type="ac_off",
        time_range="저녁",
        difficulty=DIFFICULTY_NORMAL,
        base_priority=7.0,
        score_key="saving_priority_score",
        usage_hours=2.0,
        power_fraction=1.0,
        evidence_label="저녁 시간 에어컨 끄고 자연 환기",
        is_ac_off=True,
        requires_ac=True,
    ),
    _ActionTemplate(
        action_type="timer_sleep",
        time_range="밤",
        difficulty=DIFFICULTY_EASY,
        base_priority=6.8,
        score_key="night_score",
        usage_hours=4.0,
        power_fraction=0.5,
        evidence_label="취침 타이머 설정으로 야간 에너지 절약",
        requires_ac=True,
    ),
    _ActionTemplate(
        action_type="close_window",
        time_range="오후",
        difficulty=DIFFICULTY_EASY,
        base_priority=5.0,
        score_key="cooling_loss_score",
        usage_hours=1.0,
        power_fraction=0.1,
        evidence_label="냉방 중 창문 밀폐로 냉기 손실 방지",
    ),
    _ActionTemplate(
        action_type="curtain_close",
        time_range="오전",
        difficulty=DIFFICULTY_EASY,
        base_priority=5.8,
        score_key="heat_gain_score",
        usage_hours=3.0,
        power_fraction=0.15,
        evidence_label="커튼으로 직사광선 차단",
    ),
    _ActionTemplate(
        action_type="pre_cooling",
        time_range="아침",
        difficulty=DIFFICULTY_NORMAL,
        base_priority=6.2,
        score_key="cooling_need_score",
        usage_hours=1.0,
        power_fraction=0.8,
        evidence_label="외출 전 미리 냉방하여 귀가 시 쾌적",
        requires_ac=True,
    ),
    _ActionTemplate(
        action_type="outing_ac_off",
        time_range="오전",
        difficulty=DIFFICULTY_EASY,
        base_priority=8.0,
        score_key="outing_score",
        usage_hours=3.0,
        power_fraction=1.0,
        evidence_label="외출 시 에어컨 끄기",
        is_ac_off=True,
        requires_ac=True,
    ),
    _ActionTemplate(
        action_type="natural_ventilation",
        time_range="새벽",
        difficulty=DIFFICULTY_EASY,
        base_priority=5.5,
        score_key="ventilation_score",
        usage_hours=1.0,
        power_fraction=0.2,
        evidence_label="새벽 시원한 공기로 자연 환기",
    ),
    _ActionTemplate(
        action_type="laundry_timing",
        time_range="아침",
        difficulty=DIFFICULTY_EASY,
        base_priority=4.5,
        score_key="morning_score",
        usage_hours=1.0,
        power_fraction=0.1,
        evidence_label="아침 시간 세탁으로 건조기 사용 줄이기",
    ),
    _ActionTemplate(
        action_type="electronics_off",
        time_range="밤",
        difficulty=DIFFICULTY_EASY,
        base_priority=4.0,
        score_key="saving_priority_score",
        usage_hours=6.0,
        power_fraction=0.05,
        evidence_label="대기전력 차단으로 전력 절약",
    ),
    _ActionTemplate(
        action_type="meal_timing",
        time_range="저녁",
        difficulty=DIFFICULTY_EASY,
        base_priority=4.2,
        score_key="stay_home_score",
        usage_hours=0.5,
        power_fraction=0.1,
        evidence_label="저녁 요리 시간 조정으로 열 발생 최소화",
    ),
]

# Generic fallback actions (always available, low priority)
_GENERIC_TEMPLATES: list[_ActionTemplate] = [
    _ActionTemplate(
        action_type="light_off",
        time_range="오후",
        difficulty=DIFFICULTY_EASY,
        base_priority=3.0,
        score_key="saving_priority_score",
        usage_hours=2.0,
        power_fraction=0.02,
        evidence_label="불필요한 조명 끄기",
    ),
    _ActionTemplate(
        action_type="unplug_charger",
        time_range="밤",
        difficulty=DIFFICULTY_EASY,
        base_priority=2.5,
        score_key="saving_priority_score",
        usage_hours=8.0,
        power_fraction=0.01,
        evidence_label="충전기 뽑아 대기전력 절감",
    ),
    _ActionTemplate(
        action_type="water_saving",
        time_range="아침",
        difficulty=DIFFICULTY_EASY,
        base_priority=2.0,
        score_key="saving_priority_score",
        usage_hours=0.5,
        power_fraction=0.05,
        evidence_label="절수 습관으로 에너지 절감",
    ),
]


# ---------------------------------------------------------------------------
# Lifestyle-based priority boost mapping
# ---------------------------------------------------------------------------

_LIFESTYLE_PRIORITY_BOOST: dict[str, dict[str, float]] = {
    "아침형": {"ventilation": 1.0, "laundry_timing": 1.5, "natural_ventilation": 0.5},
    "낮 활동형": {"shading": 1.0, "ac_temp_up": 0.8, "close_window": 0.5},
    "재택 체류형": {"ac_temp_up": 1.0, "fan_usage": 1.0, "timer_sleep": 0.5},
    "야간 활동형": {"timer_sleep": 1.5, "electronics_off": 1.0},
    "불규칙형": {"electronics_off": 0.5, "unplug_charger": 0.5},
    "외출 중심형": {"outing_ac_off": 1.5, "pre_cooling": 1.0},
    "냉방 고위험형": {"ac_temp_up": 1.5, "fan_usage": 1.0, "shading": 1.0, "curtain_close": 0.8},
    "절약 우선형": {"ac_temp_up": 1.0, "outing_ac_off": 1.0, "timer_sleep": 0.8, "electronics_off": 0.5},
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RecommendationCandidateService:
    """Service to build and filter recommendation action candidates.

    Generates candidates based on scores, weather, and lifestyle_type,
    with proper savings calculations via CalculationService.
    """

    def build_candidates(
        self,
        scores: Dict[str, Any],
        weather: Dict[str, Any],
        lifestyle_type: str,
        *,
        ac_power_watt: Optional[int] = None,
        room_size: Optional[str] = None,
        unit_price: Optional[int] = None,
        has_fan: bool = True,
        ac_type: str = "벽걸이",
        temperature_setting: float = 26.0,
    ) -> List[ActionCandidate]:
        """Build filtered and scored action candidates.

        Args:
            scores: Dict of score_name -> int value (0-10 from ScoringEngine)
            weather: Weather data dict with 'time_blocks' list containing
                     temperature, heat_alert, time_range per block.
            lifestyle_type: Primary lifestyle type (e.g., "아침형", "재택 체류형")
            ac_power_watt: User's AC power in watts (optional, uses room_size or default)
            room_size: Room size string for AC power estimation
            unit_price: Electricity unit price (원/kWh), defaults to 150
            has_fan: Whether user has a fan
            ac_type: AC type ("없음", "벽걸이", "스탠드", "둘 다")
            temperature_setting: Current AC temperature setting (°C)

        Returns:
            List of ActionCandidate sorted by priority_score descending,
            with min 3 and max 10 items.
        """
        # Determine if heatwave condition exists
        is_heatwave = self._detect_heatwave(weather)

        # Resolve calculation parameters
        power_watt = estimate_ac_power_watt(ac_power_watt, room_size)
        effective_unit_price = unit_price or DEFAULT_UNIT_PRICE
        temp_coeff = temperature_coefficient(temperature_setting)
        has_ac = ac_type != "없음"

        # Get lifestyle priority boosts
        lifestyle_boosts = _LIFESTYLE_PRIORITY_BOOST.get(lifestyle_type, {})

        # Build candidates from templates
        candidates: List[ActionCandidate] = []

        for template in _ACTION_TEMPLATES:
            # Skip AC-off actions during heatwave
            if is_heatwave and template.is_ac_off:
                continue

            # Skip fan actions if user has no fan
            if template.requires_fan and not has_fan:
                continue

            # Skip AC-related actions if user has no AC
            if template.requires_ac and not has_ac:
                continue

            candidate = self._build_candidate_from_template(
                template=template,
                scores=scores,
                power_watt=power_watt,
                temp_coeff=temp_coeff,
                unit_price=effective_unit_price,
                lifestyle_boosts=lifestyle_boosts,
            )
            candidates.append(candidate)

        # Sort by priority_score descending
        candidates.sort(key=lambda c: -c.priority_score)

        # Enforce max 10
        candidates = candidates[:MAX_CANDIDATES]

        # Ensure minimum 3 candidates by adding generic actions if needed
        if len(candidates) < MIN_CANDIDATES:
            candidates = self._ensure_minimum_candidates(
                candidates=candidates,
                scores=scores,
                power_watt=power_watt,
                temp_coeff=temp_coeff,
                unit_price=effective_unit_price,
                lifestyle_boosts=lifestyle_boosts,
                is_heatwave=is_heatwave,
            )

        # Assign sort_order based on final position
        for idx, candidate in enumerate(candidates, start=1):
            candidate.sort_order = idx

        return candidates

    def generate_candidates(
        self,
        *,
        user_id: UUID,
        target_date: dt.date,
        profile: Dict[str, Any],
        weather: Dict[str, Any],
        scores: Dict[str, int],
    ) -> List[ActionCandidate]:
        """Legacy method for backward compatibility with existing recommendation service.

        Delegates to build_candidates with extracted profile parameters.
        """
        energy = profile.get("energy_profile", {})
        lifestyle = profile.get("lifestyle", {})

        # Extract parameters from profile
        ac_power_watt = energy.get("ac_power_watt")
        room_size = energy.get("room_size")
        unit_price = energy.get("electricity_unit_price")
        has_fan = energy.get("has_fan", True)
        ac_type = energy.get("ac_type", "벽걸이")
        temperature_setting = energy.get("current_temperature_setting", 26.0)

        # Determine lifestyle_type from profile or default
        lifestyle_type = lifestyle.get("primary_type", "불규칙형")

        return self.build_candidates(
            scores=scores,
            weather=weather,
            lifestyle_type=lifestyle_type,
            ac_power_watt=ac_power_watt,
            room_size=room_size,
            unit_price=unit_price,
            has_fan=has_fan,
            ac_type=ac_type,
            temperature_setting=temperature_setting,
        )

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    def _detect_heatwave(self, weather: Dict[str, Any]) -> bool:
        """Check if ANY time block has temperature >= 35°C (heatwave condition)."""
        time_blocks = weather.get("time_blocks", [])
        for block in time_blocks:
            temp = block.get("temperature", 0.0)
            if temp >= HEATWAVE_THRESHOLD:
                return True
            # Also check heat_alert flag if already computed
            if block.get("heat_alert", False):
                return True
        return False

    def _build_candidate_from_template(
        self,
        *,
        template: _ActionTemplate,
        scores: Dict[str, Any],
        power_watt: int,
        temp_coeff: float,
        unit_price: int,
        lifestyle_boosts: dict[str, float],
    ) -> ActionCandidate:
        """Build a single ActionCandidate from a template with calculations."""
        # Calculate priority score (0-10 scale)
        score_value = scores.get(template.score_key, 5)
        # Normalize score to 0-10 if it's in a different range
        if isinstance(score_value, (int, float)) and score_value > 10:
            score_value = min(10, score_value / 10)

        # Base priority from template, boosted by relevant score
        raw_priority = (
            template.base_priority * (1 - template.score_weight)
            + float(score_value) * template.score_weight
        )

        # Apply lifestyle boost
        boost = lifestyle_boosts.get(template.action_type, 0.0)
        raw_priority += boost

        # Clamp to 0-10
        priority_score = round(max(0.0, min(10.0, raw_priority)), 2)

        # Calculate energy savings using CalculationService
        effective_power = int(power_watt * template.power_fraction)
        effective_power = max(1, effective_power)  # Ensure minimum 1W for valid calculation

        energy_kwh = calculate_energy_kwh(effective_power, temp_coeff, template.usage_hours)
        saving_krw = calculate_saving_krw(energy_kwh, unit_price)
        co2_kg = calculate_co2_reduction(energy_kwh)

        # Build evidence list
        evidence = [template.evidence_label]

        return ActionCandidate(
            candidate_id=f"cand_{template.action_type}_{uuid.uuid4().hex[:8]}",
            time_range=template.time_range,
            sort_order=0,  # Will be assigned after sorting
            action_type=template.action_type,
            difficulty=template.difficulty,
            priority_score=priority_score,
            estimated_saving_krw=saving_krw,
            estimated_energy_saving_kwh=energy_kwh,
            estimated_co2_reduction_kg=round(co2_kg, 3),
            evidence=evidence,
        )

    def _ensure_minimum_candidates(
        self,
        *,
        candidates: List[ActionCandidate],
        scores: Dict[str, Any],
        power_watt: int,
        temp_coeff: float,
        unit_price: int,
        lifestyle_boosts: dict[str, float],
        is_heatwave: bool,
    ) -> List[ActionCandidate]:
        """Ensure at least MIN_CANDIDATES by adding generic fallback actions."""
        existing_types = {c.action_type for c in candidates}

        for template in _GENERIC_TEMPLATES:
            if len(candidates) >= MIN_CANDIDATES:
                break
            if template.action_type in existing_types:
                continue
            # Skip AC-off generics during heatwave (shouldn't be any, but defensive)
            if is_heatwave and template.is_ac_off:
                continue

            candidate = self._build_candidate_from_template(
                template=template,
                scores=scores,
                power_watt=power_watt,
                temp_coeff=temp_coeff,
                unit_price=unit_price,
                lifestyle_boosts=lifestyle_boosts,
            )
            candidates.append(candidate)
            existing_types.add(template.action_type)

        return candidates


# ---------------------------------------------------------------------------
# Module-level helper (backward compatibility)
# ---------------------------------------------------------------------------


def _priority(scores: Dict[str, int], key: str, default: float) -> float:
    return float(scores.get(key, default) or default)


def _truthy_label(value: Any) -> str:
    return str(value) if value else ""


def _has_heat_alert(weather: Dict[str, Any]) -> bool:
    return any(block.get("heat_alert") for block in weather.get("time_blocks", []))
