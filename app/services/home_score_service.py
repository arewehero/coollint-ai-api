"""Home environment score calculation service.

Calculates heat_gain_score, cooling_loss_score, and ventilation_score
based on home environment data and current weather conditions.

Requirements: 4.2, 4.4
"""

from __future__ import annotations

from typing import Optional


def _clamp(value: int) -> int:
    """Clamp score to 0-10 integer range."""
    return max(0, min(10, int(round(value))))


def calculate_heat_gain_score(
    direction: str,
    floor_level: str,
    building_age: str,
    window_size: str,
    morning_temp: Optional[float] = None,
) -> int:
    """Calculate heat gain score (0-10).

    Higher scores indicate more heat entering the home.
    Factors: direction (south/west facing = more heat), floor (top floor = more),
    building age (old = more), window size (large = more), morning temperature.
    """
    score = 0

    # Direction factor (max +3)
    direction_scores = {
        "남향": 3,
        "남서향": 3,
        "서향": 3,
        "남동향": 2,
        "동향": 1,
        "북서향": 1,
        "북동향": 0,
        "북향": 0,
    }
    score += direction_scores.get(direction, 0)

    # Floor level factor (max +2)
    floor_scores = {
        "최상층": 2,
        "고층": 1,
        "중층": 1,
        "저층": 0,
        "1층": 0,
        "반지하": 0,
    }
    score += floor_scores.get(floor_level, 0)

    # Building age factor (max +2)
    age_scores = {
        "노후": 2,
        "보통": 1,
        "신축": 0,
    }
    score += age_scores.get(building_age, 0)

    # Window size factor (max +2)
    window_scores = {
        "큼": 2,
        "보통": 1,
        "작음": 0,
    }
    score += window_scores.get(window_size, 0)

    # Morning temperature bonus (max +2)
    if morning_temp is not None:
        if morning_temp >= 33:
            score += 2
        elif morning_temp >= 28:
            score += 1

    return _clamp(score)


def calculate_cooling_loss_score(
    insulation_level: str,
    window_sealing: str,
    ac_type: str,
) -> int:
    """Calculate cooling loss score (0-10).

    Higher scores indicate more cooling energy is being lost/wasted.
    Factors: insulation (weak = more loss), window sealing (gaps = more loss),
    ac_type (no AC = highest, as there's no cooling to begin with).
    """
    score = 0

    # Insulation level factor (max +4)
    insulation_scores = {
        "약함": 4,
        "보통": 2,
        "좋음": 0,
    }
    score += insulation_scores.get(insulation_level, 0)

    # Window sealing factor (max +3)
    sealing_scores = {
        "틈새 있음": 3,
        "보통": 1,
        "잘 막힘": 0,
    }
    score += sealing_scores.get(window_sealing, 0)

    # AC type factor (max +3)
    ac_scores = {
        "없음": 3,
        "벽걸이": 1,
        "스탠드": 0,
        "둘 다": 0,
    }
    score += ac_scores.get(ac_type, 0)

    return _clamp(score)


def calculate_ventilation_score(
    ventilation_level: str,
    rain: bool = False,
) -> int:
    """Calculate ventilation score (0-10).

    Higher scores indicate better ventilation potential.
    Factors: ventilation_level (good = higher), rain (reduces score).
    """
    score = 0

    # Ventilation level (base score, max 8)
    ventilation_scores = {
        "잘됨": 8,
        "보통": 5,
        "잘 안됨": 2,
    }
    score += ventilation_scores.get(ventilation_level, 3)

    # Rain penalty (-3)
    if rain:
        score -= 3

    return _clamp(score)
