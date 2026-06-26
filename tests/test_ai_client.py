from __future__ import annotations

import unittest

from app.services.ai_client import FallbackAIClient, MockAIClient, get_ai_client
from app.services.ai_logging import build_ai_generation_log
from app.services.ai_validation import coerce_daily_plan_copy_response


class AIClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.input_data = {
            "scores": {
                "night_score": 82,
                "saving_priority_score": 70,
            },
            "candidate_actions": [
                {
                    "candidate_id": "cand_001",
                    "time_range": "외출 전",
                    "action_type": "shading_before_outing",
                    "estimated_saving_krw": 150,
                    "estimated_energy_saving_kwh": 0.3,
                    "estimated_co2_reduction_kg": 0.14,
                    "evidence": ["서향", "큰 창문"],
                }
            ],
        }

    def test_mock_lifestyle_analysis_returns_contract_shape(self) -> None:
        response = MockAIClient().analyze_lifestyle(self.input_data)

        self.assertEqual(response.primary_type, "야간 활동형")
        self.assertEqual(response.secondary_type, "절약 우선형")
        self.assertGreaterEqual(response.confidence, 0)
        self.assertLessEqual(response.confidence, 1)

    def test_mock_daily_plan_copy_uses_candidate_ids_without_savings_values(self) -> None:
        response = MockAIClient().generate_daily_plan_copy(self.input_data)
        dumped = response.model_dump()

        self.assertEqual(dumped["actions"][0]["candidate_id"], "cand_001")
        self.assertIn("cheer_message", dumped)
        self.assertNotIn("estimated_saving_krw", dumped["actions"][0])
        self.assertNotIn("estimated_energy_saving_kwh", dumped["actions"][0])
        self.assertNotIn("estimated_co2_reduction_kg", dumped["actions"][0])

    def test_invalid_daily_plan_copy_falls_back_to_template(self) -> None:
        invalid_response = {
            "cheer_message": "invalid",
            "actions": [
                {
                    "candidate_id": "wrong_id",
                    "title": "bad",
                    "action": "bad",
                    "reason": "bad",
                }
            ],
        }

        response = coerce_daily_plan_copy_response(invalid_response, self.input_data)

        self.assertEqual(response.actions[0].candidate_id, "cand_001")
        self.assertTrue(response.actions[0].title)

    def test_unknown_provider_uses_fallback_client(self) -> None:
        self.assertIsInstance(get_ai_client("unknown"), FallbackAIClient)

    def test_ai_log_payload_disabled_by_default(self) -> None:
        log = build_ai_generation_log(
            user_id=None,
            request_type="daily_plan",
            prompt_version="test",
            model_name="mock-ai-client",
            success=True,
            latency_ms=10,
            request_payload={"hello": "world"},
            response_payload={"ok": True},
            log_payload=False,
        )

        self.assertIsNotNone(log.input_hash)
        self.assertIsNone(log.request_payload)
        self.assertIsNone(log.response_payload)


if __name__ == "__main__":
    unittest.main()
