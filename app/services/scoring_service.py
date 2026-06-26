"""Scoring service for lifestyle and home environment score calculations.

Calculates 12 scores (all clamped to 0-10 integer range) and derives dominant_signals.

Requirements: 4.1, 4.2, 4.3, 4.4
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.home_score_service import (
    calculate_cooling_loss_score,
    calculate_heat_gain_score,
    calculate_ventilation_score,
)


def _clamp(value: int) -> int:
    """Clamp score to 0-10 integer range."""
    return max(0, min(10, int(round(value))))


# ---------------------------------------------------------------------------
# Lifestyle Scores (1-9)
# ---------------------------------------------------------------------------


def _calculate_morning_score(lifestyle: Dict[str, Any]) -> int:
    """Morning score: high if main_activity_time=아침형.

    Score 1: morning_score
    """
    score = 0
    if lifestyle.get("main_activity_time") == "아침형":
        score += 8
    # Bonus if sleep_time is 밤 (early sleeper = morning person)
    if lifestyle.get("sleep_time") == "밤":
        score += 2
    return _clamp(score)


def _calculate_daytime_score(lifestyle: Dict[str, Any]) -> int:
    """Daytime score: high if main_activity_time=낮 활동, daytime_home_stay 높을수록.

    Score 2: daytime_score
    """
    score = 0
    if lifestyle.get("main_activity_time") == "낮 활동":
        score += 5

    daytime_stay_scores = {
        "종일 재택": 4,
        "오후 오래": 3,
        "오후 잠깐": 1,
        "거의 없음": 0,
    }
    score += daytime_stay_scores.get(lifestyle.get("daytime_home_stay", ""), 0)

    return _clamp(score)


def _calculate_night_score(lifestyle: Dict[str, Any]) -> int:
    """Night score: high if main_activity_time=야간 활동, sleep_time=새벽.

    Score 3: night_score
    """
    score = 0
    if lifestyle.get("main_activity_time") == "야간 활동":
        score += 6
    if lifestyle.get("sleep_time") == "새벽":
        score += 4
    return _clamp(score)


def _calculate_irregular_score(lifestyle: Dict[str, Any]) -> int:
    """Irregular score: high if main_activity_time=불규칙, sleep_time=불규칙.

    Score 4: irregular_score
    """
    score = 0
    if lifestyle.get("main_activity_time") == "불규칙":
        score += 6
    if lifestyle.get("sleep_time") == "불규칙":
        score += 4
    return _clamp(score)


def _calculate_stay_home_score(lifestyle: Dict[str, Any]) -> int:
    """Stay home score: high if daytime_home_stay 높음, hot_time_home_stay 높음.

    Score 5: stay_home_score
    """
    score = 0

    daytime_stay_scores = {
        "종일 재택": 5,
        "오후 오래": 3,
        "오후 잠깐": 1,
        "거의 없음": 0,
    }
    score += daytime_stay_scores.get(lifestyle.get("daytime_home_stay", ""), 0)

    hot_stay_scores = {
        "거의 항상": 5,
        "자주": 3,
        "가끔": 1,
        "아니요": 0,
    }
    score += hot_stay_scores.get(lifestyle.get("hot_time_home_stay", ""), 0)

    return _clamp(score)


def _calculate_outing_score(lifestyle: Dict[str, Any]) -> int:
    """Outing score: high if outdoor_activity 많음, daytime_home_stay 낮음.

    Score 6: outing_score
    """
    score = 0

    outdoor_scores = {
        "많음": 5,
        "보통": 3,
        "적음": 0,
    }
    score += outdoor_scores.get(lifestyle.get("outdoor_activity", ""), 0)

    # Low daytime_home_stay = more outing
    daytime_outing_scores = {
        "거의 없음": 5,
        "오후 잠깐": 3,
        "오후 오래": 1,
        "종일 재택": 0,
    }
    score += daytime_outing_scores.get(lifestyle.get("daytime_home_stay", ""), 0)

    return _clamp(score)


def _calculate_cooling_need_score(
    lifestyle: Dict[str, Any], energy: Optional[Dict[str, Any]] = None
) -> int:
    """Cooling need score: high if hot_time_home_stay 높음, comfort_preference=시원한 편 선호.

    Score 7: cooling_need_score
    """
    score = 0

    hot_stay_scores = {
        "거의 항상": 5,
        "자주": 3,
        "가끔": 1,
        "아니요": 0,
    }
    score += hot_stay_scores.get(lifestyle.get("hot_time_home_stay", ""), 0)

    if energy:
        if energy.get("comfort_preference") == "시원한 편 선호":
            score += 5
        elif energy.get("comfort_preference") == "보통":
            score += 2

    return _clamp(score)


def _calculate_saving_priority_score(
    lifestyle: Dict[str, Any], energy: Optional[Dict[str, Any]] = None
) -> int:
    """Saving priority score: high if comfort_preference=절약 우선, monthly_goal_bill set.

    Score 8: saving_priority_score
    """
    score = 0

    if energy:
        if energy.get("comfort_preference") == "절약 우선":
            score += 6
        elif energy.get("comfort_preference") == "보통":
            score += 2

        # Having a goal bill set indicates saving priority
        if energy.get("monthly_goal_bill") is not None:
            score += 4

    return _clamp(score)


def _calculate_saving_opportunity_score(
    energy: Optional[Dict[str, Any]] = None,
) -> int:
    """Saving opportunity score: high if monthly_electricity_bill 높음, ac_type 있음.

    Score 9: saving_opportunity_score
    """
    score = 0

    if energy:
        # Higher bill = more opportunity to save
        bill = energy.get("monthly_electricity_bill", 0) or 0
        if bill >= 150_000:
            score += 5
        elif bill >= 100_000:
            score += 4
        elif bill >= 70_000:
            score += 3
        elif bill >= 40_000:
            score += 2
        elif bill >= 20_000:
            score += 1

        # Having AC means more saving opportunity
        ac_type = energy.get("ac_type", "없음")
        if ac_type == "둘 다":
            score += 5
        elif ac_type == "스탠드":
            score += 4
        elif ac_type == "벽걸이":
            score += 3
        elif ac_type == "없음":
            score += 0

    return _clamp(score)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_lifestyle_scores(
    lifestyle: Dict[str, Any],
    energy: Optional[Dict[str, Any]] = None,
) -> Dict[str, int]:
    """Calculate all 9 lifestyle-based scores.

    Args:
        lifestyle: Lifestyle data (main_activity_time, daytime_home_stay, etc.)
        energy: Energy profile data (comfort_preference, monthly_electricity_bill, etc.)

    Returns:
        Dict with 9 score fields, all integers 0-10.
    """
    return {
        "morning_score": _calculate_morning_score(lifestyle),
        "daytime_score": _calculate_daytime_score(lifestyle),
        "night_score": _calculate_night_score(lifestyle),
        "irregular_score": _calculate_irregular_score(lifestyle),
        "stay_home_score": _calculate_stay_home_score(lifestyle),
        "outing_score": _calculate_outing_score(lifestyle),
        "cooling_need_score": _calculate_cooling_need_score(lifestyle, energy),
        "saving_priority_score": _calculate_saving_priority_score(lifestyle, energy),
        "saving_opportunity_score": _calculate_saving_opportunity_score(energy),
    }


def calculate_home_scores(
    home_env: Dict[str, Any],
    weather: Optional[Dict[str, Any]] = None,
    energy: Optional[Dict[str, Any]] = None,
) -> Dict[str, int]:
    """Calculate all 3 home environment scores.

    Args:
        home_env: Home environment data (direction, floor_level, etc.)
        weather: Weather data with keys 'morning_temp' and 'rain'.
        energy: Energy profile data (ac_type).

    Returns:
        Dict with 3 score fields, all integers 0-10.
    """
    morning_temp = None
    rain = False
    if weather:
        morning_temp = weather.get("morning_temp")
        rain = weather.get("rain", False)

    ac_type = "없음"
    if energy:
        ac_type = energy.get("ac_type", "없음")

    return {
        "heat_gain_score": calculate_heat_gain_score(
            direction=home_env.get("direction", "북향"),
            floor_level=home_env.get("floor_level", "중층"),
            building_age=home_env.get("building_age", "보통"),
            window_size=home_env.get("window_size", "보통"),
            morning_temp=morning_temp,
        ),
        "cooling_loss_score": calculate_cooling_loss_score(
            insulation_level=home_env.get("insulation_level", "보통"),
            window_sealing=home_env.get("window_sealing", "보통"),
            ac_type=ac_type,
        ),
        "ventilation_score": calculate_ventilation_score(
            ventilation_level=home_env.get("ventilation_level", "보통"),
            rain=rain,
        ),
    }


def calculate_all_scores(
    lifestyle: Dict[str, Any],
    home_env: Dict[str, Any],
    energy: Optional[Dict[str, Any]] = None,
    weather: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculate all 12 scores and dominant_signals.

    Args:
        lifestyle: Lifestyle input data.
        home_env: Home environment data.
        energy: Energy profile data.
        weather: Weather data dict with 'morning_temp' (float) and 'rain' (bool).

    Returns:
        Dict with all 12 score fields (int 0-10) and dominant_signals (list of str).
    """
    lifestyle_scores = calculate_lifestyle_scores(lifestyle, energy)
    home_scores = calculate_home_scores(home_env, weather, energy)

    all_scores = {**lifestyle_scores, **home_scores}

    # Ensure all scores are clamped (defensive)
    for key in all_scores:
        all_scores[key] = _clamp(all_scores[key])

    # Calculate dominant_signals: top 3 scores >= 7, sorted by value descending
    all_scores["dominant_signals"] = derive_dominant_signals(all_scores)

    return all_scores


def derive_dominant_signals(scores: Dict[str, int]) -> List[str]:
    """Derive dominant_signals from calculated scores.

    Returns the top 3 score field names where score >= 7,
    sorted by value descending.

    Args:
        scores: Dict of score_name -> int value (0-10)

    Returns:
        List of score field names (max 3)
    """
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

    # Filter scores >= 7 and sort by value descending
    high_scores = [
        (name, scores.get(name, 0))
        for name in score_fields
        if scores.get(name, 0) >= 7
    ]
    high_scores.sort(key=lambda x: x[1], reverse=True)

    # Return top 3
    return [name for name, _ in high_scores[:3]]
