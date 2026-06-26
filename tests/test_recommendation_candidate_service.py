"""Unit tests for RecommendationCandidateService.build_candidates.

Tests cover:
1. Normal case: 3-10 actions with proper calculations
2. Heatwave case: No AC-off actions when temperature >= 35°C
3. Edge case: At least 3 generic candidates when few templates apply

Requirements: 6.3, 6.5, 6.6
"""

from __future__ import annotations

import pytest

from app.services.recommendation_candidate_service import (
    AC_OFF_ACTION_TYPES,
    HEATWAVE_THRESHOLD,
    MAX_CANDIDATES,
    MIN_CANDIDATES,
    ActionCandidate,
    RecommendationCandidateService,
)


@pytest.fixture()
def service() -> RecommendationCandidateService:
    return RecommendationCandidateService()


@pytest.fixture()
def normal_scores() -> dict[str, int]:
    return {
        "morning_score": 5,
        "daytime_score": 6,
        "night_score": 7,
        "irregular_score": 3,
        "stay_home_score": 5,
        "outing_score": 6,
        "cooling_need_score": 7,
        "saving_priority_score": 8,
        "saving_opportunity_score": 6,
        "heat_gain_score": 7,
        "cooling_loss_score": 5,
        "ventilation_score": 6,
    }


@pytest.fixture()
def normal_weather() -> dict:
    return {
        "time_blocks": [
            {"time_range": "새벽", "temperature": 22.0, "heat_alert": False},
            {"time_range": "아침", "temperature": 25.0, "heat_alert": False},
            {"time_range": "오전", "temperature": 28.0, "heat_alert": False},
            {"time_range": "오후", "temperature": 32.0, "heat_alert": False},
            {"time_range": "저녁", "temperature": 29.0, "heat_alert": False},
            {"time_range": "밤", "temperature": 26.0, "heat_alert": False},
        ]
    }


@pytest.fixture()
def heatwave_weather() -> dict:
    """Weather with at least one block >= 35°C."""
    return {
        "time_blocks": [
            {"time_range": "새벽", "temperature": 27.0, "heat_alert": False},
            {"time_range": "아침", "temperature": 30.0, "heat_alert": False},
            {"time_range": "오전", "temperature": 34.0, "heat_alert": False},
            {"time_range": "오후", "temperature": 36.5, "heat_alert": True},
            {"time_range": "저녁", "temperature": 35.0, "heat_alert": True},
            {"time_range": "밤", "temperature": 30.0, "heat_alert": False},
        ]
    }


class TestNormalCase:
    """Test normal candidate generation (3-10 actions with calculations)."""

    def test_returns_between_3_and_10_candidates(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
        )

        assert MIN_CANDIDATES <= len(candidates) <= MAX_CANDIDATES

    def test_candidates_are_sorted_by_priority_descending(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
        )

        priorities = [c.priority_score for c in candidates]
        assert priorities == sorted(priorities, reverse=True)

    def test_each_candidate_has_required_fields(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
        )

        for candidate in candidates:
            assert candidate.candidate_id
            assert candidate.time_range in ["새벽", "아침", "오전", "오후", "저녁", "밤"]
            assert candidate.sort_order >= 1
            assert candidate.action_type
            assert candidate.difficulty in ["쉬움", "보통", "약간 어려움"]
            assert 0 <= candidate.priority_score <= 10
            assert candidate.estimated_saving_krw >= 0
            assert candidate.estimated_energy_saving_kwh >= 0
            assert candidate.estimated_co2_reduction_kg >= 0
            assert len(candidate.evidence) >= 1

    def test_savings_calculated_using_calculation_service(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        """Verify savings are calculated (non-zero for typical actions)."""
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
        )

        # At least some candidates should have non-zero savings
        total_krw = sum(c.estimated_saving_krw for c in candidates)
        total_kwh = sum(c.estimated_energy_saving_kwh for c in candidates)
        total_co2 = sum(c.estimated_co2_reduction_kg for c in candidates)

        assert total_krw > 0
        assert total_kwh > 0
        assert total_co2 > 0

    def test_sort_order_assigned_sequentially(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
        )

        sort_orders = [c.sort_order for c in candidates]
        assert sort_orders == list(range(1, len(candidates) + 1))


class TestHeatwaveCase:
    """Test heatwave filtering: No AC-off actions when T >= 35°C."""

    def test_no_ac_off_actions_during_heatwave(
        self, service: RecommendationCandidateService, normal_scores: dict, heatwave_weather: dict
    ) -> None:
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=heatwave_weather,
            lifestyle_type="재택 체류형",
        )

        ac_off_candidates = [
            c for c in candidates if c.action_type in AC_OFF_ACTION_TYPES
        ]
        assert len(ac_off_candidates) == 0

    def test_heatwave_still_produces_valid_candidate_count(
        self, service: RecommendationCandidateService, normal_scores: dict, heatwave_weather: dict
    ) -> None:
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=heatwave_weather,
            lifestyle_type="재택 체류형",
        )

        assert MIN_CANDIDATES <= len(candidates) <= MAX_CANDIDATES

    def test_normal_weather_can_include_ac_off(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        """Verify ac_off actions ARE included when no heatwave."""
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
        )

        ac_off_candidates = [
            c for c in candidates
            if c.action_type in AC_OFF_ACTION_TYPES or c.action_type == "outing_ac_off"
        ]
        # At least one AC-off action should be present in normal conditions
        assert len(ac_off_candidates) >= 1

    def test_exact_35_degrees_triggers_heatwave(
        self, service: RecommendationCandidateService, normal_scores: dict
    ) -> None:
        """35.0°C exactly should trigger heatwave filtering."""
        weather = {
            "time_blocks": [
                {"time_range": "오후", "temperature": 35.0, "heat_alert": True},
            ]
        }

        candidates = service.build_candidates(
            scores=normal_scores,
            weather=weather,
            lifestyle_type="재택 체류형",
        )

        ac_off_candidates = [c for c in candidates if c.action_type in AC_OFF_ACTION_TYPES]
        assert len(ac_off_candidates) == 0

    def test_just_below_35_allows_ac_off(
        self, service: RecommendationCandidateService, normal_scores: dict
    ) -> None:
        """34.9°C should NOT trigger heatwave filtering."""
        weather = {
            "time_blocks": [
                {"time_range": "오후", "temperature": 34.9, "heat_alert": False},
            ]
        }

        candidates = service.build_candidates(
            scores=normal_scores,
            weather=weather,
            lifestyle_type="재택 체류형",
        )

        ac_off_candidates = [
            c for c in candidates
            if c.action_type in AC_OFF_ACTION_TYPES or c.action_type == "outing_ac_off"
        ]
        assert len(ac_off_candidates) >= 1


class TestMinimumCandidatesEdgeCase:
    """Test that at least 3 candidates are always generated."""

    def test_minimum_3_when_no_ac_no_fan(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        """When user has no AC and no fan, fewer templates apply but still get 3+."""
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
            ac_type="없음",
            has_fan=False,
        )

        assert len(candidates) >= MIN_CANDIDATES

    def test_minimum_3_during_heatwave_no_ac(
        self, service: RecommendationCandidateService, normal_scores: dict, heatwave_weather: dict
    ) -> None:
        """Edge case: heatwave + no AC — still get at least 3."""
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=heatwave_weather,
            lifestyle_type="재택 체류형",
            ac_type="없음",
            has_fan=False,
        )

        assert len(candidates) >= MIN_CANDIDATES


class TestLifestyleTypeBoost:
    """Test that lifestyle type affects priority ordering."""

    def test_morning_type_boosts_morning_actions(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        morning_candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="아침형",
        )

        # Find ventilation action priority
        ventilation = next(
            (c for c in morning_candidates if c.action_type == "ventilation"), None
        )
        assert ventilation is not None

        # Compare with non-morning type
        other_candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="야간 활동형",
        )
        other_ventilation = next(
            (c for c in other_candidates if c.action_type == "ventilation"), None
        )

        if other_ventilation:
            # Morning type should give higher priority to ventilation
            assert ventilation.priority_score > other_ventilation.priority_score

    def test_unknown_lifestyle_type_produces_valid_result(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        """Unknown lifestyle type should not crash, just no boost."""
        candidates = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="unknown_type",
        )

        assert MIN_CANDIDATES <= len(candidates) <= MAX_CANDIDATES


class TestCalculationParameters:
    """Test that calculation parameters are properly passed through."""

    def test_custom_unit_price_affects_saving_krw(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        cheap = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
            unit_price=100,
        )
        expensive = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
            unit_price=500,
        )

        total_cheap = sum(c.estimated_saving_krw for c in cheap)
        total_expensive = sum(c.estimated_saving_krw for c in expensive)
        assert total_expensive > total_cheap

    def test_custom_ac_power_affects_savings(
        self, service: RecommendationCandidateService, normal_scores: dict, normal_weather: dict
    ) -> None:
        low_power = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
            ac_power_watt=750,
        )
        high_power = service.build_candidates(
            scores=normal_scores,
            weather=normal_weather,
            lifestyle_type="재택 체류형",
            ac_power_watt=3000,
        )

        total_low = sum(c.estimated_saving_krw for c in low_power)
        total_high = sum(c.estimated_saving_krw for c in high_power)
        assert total_high > total_low
