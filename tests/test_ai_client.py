from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.ai_client import (
    AIClientError,
    AITimeoutError,
    BedrockAIClient,
    FallbackAIClient,
    MockAIClient,
    get_ai_client,
)
from app.services.ai_logging import build_ai_generation_log
from app.services.ai_validation import coerce_daily_plan_copy_response


VALID_LIFESTYLE_TYPES = [
    "아침형", "낮 활동형", "재택 체류형", "야간 활동형",
    "불규칙형", "외출 중심형", "냉방 고위험형", "절약 우선형",
]


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


class BedrockAIClientTests(unittest.TestCase):
    """Tests for BedrockAIClient and AI exception classes."""

    def test_get_ai_client_bedrock_returns_bedrock_instance(self) -> None:
        client = get_ai_client("bedrock")
        self.assertIsInstance(client, BedrockAIClient)

    def test_bedrock_client_has_correct_provider(self) -> None:
        client = BedrockAIClient()
        self.assertEqual(client.provider, "bedrock")

    def test_bedrock_client_uses_settings_timeout(self) -> None:
        client = BedrockAIClient()
        self.assertEqual(client.timeout_seconds, 8)

    def test_bedrock_client_custom_timeout(self) -> None:
        client = BedrockAIClient(timeout_seconds=10)
        self.assertEqual(client.timeout_seconds, 10)

    def test_ai_timeout_error_is_subclass_of_ai_client_error(self) -> None:
        self.assertTrue(issubclass(AITimeoutError, AIClientError))

    def test_ai_client_error_is_subclass_of_exception(self) -> None:
        self.assertTrue(issubclass(AIClientError, Exception))

    def test_bedrock_analyze_lifestyle_raises_timeout_on_read_timeout(self) -> None:
        """Simulate a botocore ReadTimeoutError during invoke_model."""
        client = BedrockAIClient()

        mock_boto_client = MagicMock()

        # Create a custom exception class with "timeout" in the name
        class ReadTimeoutError(Exception):
            pass

        mock_boto_client.invoke_model.side_effect = ReadTimeoutError("Read timeout on endpoint URL")

        client._client = mock_boto_client

        with self.assertRaises(AITimeoutError) as ctx:
            client.analyze_lifestyle({"scores": {"morning_score": 8}})

        self.assertIn("timed out", str(ctx.exception))

    def test_bedrock_analyze_lifestyle_raises_client_error_on_generic_failure(self) -> None:
        """Simulate a generic AWS error during invoke_model."""
        client = BedrockAIClient()

        mock_boto_client = MagicMock()
        mock_boto_client.invoke_model.side_effect = RuntimeError("Service unavailable")

        client._client = mock_boto_client

        with self.assertRaises(AIClientError):
            client.analyze_lifestyle({"scores": {"morning_score": 8}})

    def test_bedrock_analyze_lifestyle_raises_on_invalid_json_response(self) -> None:
        """Simulate a Bedrock response with invalid JSON content."""
        import io

        client = BedrockAIClient()

        mock_boto_client = MagicMock()
        # Claude returns content blocks; simulate invalid JSON in text
        response_body = b'{"content": [{"type": "text", "text": "not json"}]}'
        mock_boto_client.invoke_model.return_value = {
            "body": io.BytesIO(response_body),
        }

        client._client = mock_boto_client

        with self.assertRaises(AIClientError) as ctx:
            client.analyze_lifestyle({"scores": {"morning_score": 8}})

        self.assertIn("parse", str(ctx.exception).lower())

    def test_bedrock_analyze_lifestyle_raises_on_validation_failure(self) -> None:
        """Simulate a valid JSON response but with invalid lifestyle data."""
        import io
        import json

        client = BedrockAIClient()

        mock_boto_client = MagicMock()
        # JSON is valid but primary_type is invalid
        invalid_lifestyle = json.dumps({
            "primary_type": "잘못된유형",
            "secondary_type": None,
            "confidence": 0.9,
            "summary": "테스트",
            "reason": "테스트 이유",
        })
        response_body = json.dumps({
            "content": [{"type": "text", "text": invalid_lifestyle}]
        }).encode()
        mock_boto_client.invoke_model.return_value = {
            "body": io.BytesIO(response_body),
        }

        client._client = mock_boto_client

        # The schema doesn't restrict primary_type values at the Pydantic level
        # (only min/max length), so validation passes. The validator in
        # ai_validation_service is what checks the 8 types.
        # Here we test with a truly invalid response (missing field).
        invalid_response_missing_field = json.dumps({
            "primary_type": "아침형",
            "confidence": 0.9,
            "summary": "테스트",
            # missing "reason" field
        })
        response_body2 = json.dumps({
            "content": [{"type": "text", "text": invalid_response_missing_field}]
        }).encode()
        mock_boto_client.invoke_model.return_value = {
            "body": io.BytesIO(response_body2),
        }

        with self.assertRaises(AIClientError) as ctx:
            client.analyze_lifestyle({"scores": {"morning_score": 8}})

        self.assertIn("validation failed", str(ctx.exception).lower())

    def test_bedrock_analyze_lifestyle_success(self) -> None:
        """Simulate a successful Bedrock response with valid lifestyle data."""
        import io
        import json

        client = BedrockAIClient()

        mock_boto_client = MagicMock()
        valid_lifestyle = json.dumps({
            "primary_type": "재택 체류형",
            "secondary_type": "절약 우선형",
            "confidence": 0.87,
            "summary": "재택 근무를 하며 절약에 관심이 많은 사용자입니다.",
            "reason": "높은 재택 점수와 절약 우선 점수를 기반으로 판단했습니다.",
        })
        response_body = json.dumps({
            "content": [{"type": "text", "text": valid_lifestyle}]
        }).encode()
        mock_boto_client.invoke_model.return_value = {
            "body": io.BytesIO(response_body),
        }

        client._client = mock_boto_client

        result = client.analyze_lifestyle({"scores": {"stay_home_score": 9}})

        self.assertEqual(result.primary_type, "재택 체류형")
        self.assertEqual(result.secondary_type, "절약 우선형")
        self.assertAlmostEqual(result.confidence, 0.87)
        self.assertIn("재택", result.summary)

    def test_mock_analyze_lifestyle_returns_valid_types(self) -> None:
        """Mock client should always return types from the 8 valid types list."""
        test_cases = [
            {"scores": {"morning_score": 10}},
            {"scores": {"night_score": 8, "saving_priority_score": 7}},
            {"scores": {}},
            {"profile": {"lifestyle": {"main_activity_time": "아침형"}}},
        ]

        for input_data in test_cases:
            response = MockAIClient().analyze_lifestyle(input_data)
            self.assertIn(response.primary_type, VALID_LIFESTYLE_TYPES)
            if response.secondary_type is not None:
                self.assertIn(response.secondary_type, VALID_LIFESTYLE_TYPES)
            self.assertGreaterEqual(response.confidence, 0.0)
            self.assertLessEqual(response.confidence, 1.0)
            self.assertGreaterEqual(len(response.summary), 1)
            self.assertLessEqual(len(response.summary), 200)


if __name__ == "__main__":
    unittest.main()
