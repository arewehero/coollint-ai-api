"""Fallback strategy integration tests.

Verifies the fallback chain behavior when external services fail:
1. Weather API failure → expired cache → WEATHER_UNAVAILABLE (503)
2. AI Lifestyle failure → score-based rule fallback (fallback_lifestyle_type)
3. AI Recommendation failure → fallback template (status="fallback")

Requirements: 12.1, 12.2, 12.5
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.core.errors import ApiException
from app.routers.analysis import fallback_lifestyle_type
from app.services.ai_client import AIClientError, FallbackAIClient
from app.services.weather_provider import WeatherProviderError
from app.services.weather_service import WeatherService


class TestWeatherFallbackChain(unittest.TestCase):
    """Weather API 실패 → 만료된 캐시 → 503 체인 검증.

    Requirements: 12.1
    """

    def setUp(self) -> None:
        self.mock_repo = MagicMock()
        self.mock_provider = MagicMock()
        self.service = WeatherService(
            weather_repository=self.mock_repo,
            weather_provider=self.mock_provider,
        )
        self.mock_db = MagicMock()

    def test_provider_failure_with_no_cache_raises_weather_unavailable(self) -> None:
        """Weather API 실패 + 캐시 없음 → 503 WEATHER_UNAVAILABLE."""
        # No valid cache
        self.mock_repo.get_cached_snapshot.return_value = None
        # Provider fails
        self.mock_provider.fetch_forecast.side_effect = WeatherProviderError("API down")
        # No expired cache either
        self.mock_repo.get_expired_snapshot.return_value = None

        with self.assertRaises(ApiException) as ctx:
            self.service.get_hourly_weather(self.mock_db, date=None)

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.code, "WEATHER_UNAVAILABLE")

    def test_provider_failure_with_expired_cache_returns_cached_data(self) -> None:
        """Weather API 실패 + 만료된 캐시 존재 → 만료된 캐시 반환."""
        # No valid cache
        self.mock_repo.get_cached_snapshot.return_value = None
        # Provider fails
        self.mock_provider.fetch_forecast.side_effect = WeatherProviderError("timeout")

        # Expired cache exists - mock a snapshot with time_blocks
        expired_snapshot = MagicMock()
        expired_snapshot.date = "2025-07-01"
        mock_block = MagicMock()
        mock_block.time_range = "오전"
        mock_block.temperature = 28.5
        mock_block.feels_like = 30.0
        mock_block.humidity = 65
        mock_block.rain = False
        mock_block.heat_alert = False
        expired_snapshot.time_blocks = [mock_block]

        self.mock_repo.get_expired_snapshot.return_value = expired_snapshot

        result = self.service.get_hourly_weather(self.mock_db, date=None)

        self.assertTrue(result.cached)
        self.assertEqual(len(result.time_blocks), 1)
        self.assertEqual(result.time_blocks[0].time_range, "오전")


class TestAILifestyleFallback(unittest.TestCase):
    """AI Lifestyle 실패 → 점수 기반 규칙 판단 폴백 검증.

    Requirements: 12.2
    """

    def test_fallback_returns_max_score_type(self) -> None:
        """fallback_lifestyle_type은 가장 높은 점수의 유형을 반환해야 한다."""
        scores = {
            "morning_score": 3,
            "daytime_score": 5,
            "night_score": 9,
            "irregular_score": 2,
            "stay_home_score": 4,
            "outing_score": 1,
            "cooling_need_score": 6,
            "saving_priority_score": 7,
        }

        result = fallback_lifestyle_type(scores)
        self.assertEqual(result, "야간 활동형")

    def test_fallback_with_saving_priority_highest(self) -> None:
        """절약 우선형 점수가 가장 높을 때 '절약 우선형' 반환."""
        scores = {
            "morning_score": 3,
            "daytime_score": 5,
            "night_score": 4,
            "irregular_score": 2,
            "stay_home_score": 4,
            "outing_score": 1,
            "cooling_need_score": 6,
            "saving_priority_score": 10,
        }

        result = fallback_lifestyle_type(scores)
        self.assertEqual(result, "절약 우선형")

    def test_fallback_with_empty_scores_returns_default(self) -> None:
        """빈 점수 딕셔너리 시 기본값 '불규칙형' 반환."""
        result = fallback_lifestyle_type({})
        self.assertEqual(result, "불규칙형")

    def test_fallback_ignores_non_mapped_score_keys(self) -> None:
        """매핑되지 않은 키(예: ventilation_score)는 무시한다."""
        scores = {
            "ventilation_score": 99,
            "heat_gain_score": 99,
            "morning_score": 5,
        }

        result = fallback_lifestyle_type(scores)
        self.assertEqual(result, "아침형")


class TestAIRecommendationFallback(unittest.TestCase):
    """AI Recommendation 실패 → 폴백 템플릿 (status="fallback") 검증.

    Requirements: 12.5
    """

    def test_fallback_client_generates_plan_copy_with_template(self) -> None:
        """FallbackAIClient는 후보 행동에 대해 폴백 템플릿 응답을 생성해야 한다."""
        input_data = {
            "user_id": "test-user-001",
            "date": "2025-07-01",
            "lifestyle_analysis": {
                "primary_type": "재택 체류형",
                "secondary_type": "절약 우선형",
                "confidence": 0.6,
                "summary": "재택 체류형 특성을 기준으로 절약 행동을 우선 추천합니다.",
                "reason": "AI 분석 불가",
            },
            "candidate_actions": [
                {
                    "candidate_id": "cand_001",
                    "time_range": "오전",
                    "action_type": "shading_before_outing",
                    "estimated_saving_krw": 150,
                    "estimated_energy_saving_kwh": 0.3,
                    "estimated_co2_reduction_kg": 0.14,
                    "evidence": ["서향", "큰 창문"],
                    "difficulty": "easy",
                    "priority_score": 8.5,
                },
                {
                    "candidate_id": "cand_002",
                    "time_range": "오후",
                    "action_type": "ac_temp_up",
                    "estimated_saving_krw": 200,
                    "estimated_energy_saving_kwh": 0.5,
                    "estimated_co2_reduction_kg": 0.24,
                    "evidence": ["높은 설정온도 여유"],
                    "difficulty": "medium",
                    "priority_score": 7.0,
                },
            ],
        }

        fallback_client = FallbackAIClient()
        response = fallback_client.generate_daily_plan_copy(input_data)

        # Verify template generates valid structure
        self.assertIsNotNone(response.cheer_message)
        self.assertGreater(len(response.cheer_message), 0)
        self.assertEqual(len(response.actions), 2)

        # Each action should have the matching candidate_id
        action_ids = [a.candidate_id for a in response.actions]
        self.assertIn("cand_001", action_ids)
        self.assertIn("cand_002", action_ids)

        # Each action should have title, action, reason
        for action in response.actions:
            self.assertIsNotNone(action.title)
            self.assertGreater(len(action.title), 0)
            self.assertIsNotNone(action.action)
            self.assertIsNotNone(action.reason)

    def test_recommendation_service_uses_fallback_on_ai_failure(self) -> None:
        """AI 호출 실패 시 RecommendationService가 FallbackAIClient로 전환하여 status='fallback'으로 처리."""
        from app.services.recommendation_service import DailyRecommendationService

        # Create a mock AI client that always fails
        mock_ai_client = MagicMock()
        mock_ai_client.generate_daily_plan_copy.side_effect = AIClientError("Bedrock unavailable")
        mock_ai_client.prompt_version = "v1"
        mock_ai_client.model_name = "test-model"

        service = DailyRecommendationService(
            profile_repository=MagicMock(),
            recommendation_repository=MagicMock(),
            weather_adapter=MagicMock(),
            scoring_adapter=MagicMock(),
            candidate_service=MagicMock(),
            ai_client=mock_ai_client,
        )

        # Test the private helper that handles AI fallback
        input_data = {
            "user_id": "test-user",
            "date": "2025-07-01",
            "lifestyle_analysis": {
                "primary_type": "아침형",
                "secondary_type": None,
                "confidence": 0.8,
                "summary": "아침형",
                "reason": "test",
            },
            "candidate_actions": [
                {
                    "candidate_id": "cand_001",
                    "time_range": "아침",
                    "action_type": "ventilation",
                    "estimated_saving_krw": 100,
                    "estimated_energy_saving_kwh": 0.2,
                    "estimated_co2_reduction_kg": 0.1,
                    "evidence": [],
                    "difficulty": "easy",
                    "priority_score": 7.5,
                },
            ],
        }

        mock_db = MagicMock()
        response = service._generate_daily_plan_copy(db=mock_db, user_id="test-user", input_data=input_data)

        # The service should have used fallback
        self.assertTrue(service._last_copy_used_fallback)
        # The response should still be valid (from FallbackAIClient)
        self.assertIsNotNone(response.cheer_message)
        self.assertEqual(len(response.actions), 1)
        self.assertEqual(response.actions[0].candidate_id, "cand_001")


if __name__ == "__main__":
    unittest.main()
