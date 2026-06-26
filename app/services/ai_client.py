from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Protocol

from app.core.config import settings
from app.schemas.ai import DailyPlanCopyAIResponse, LifestyleAnalysisAIResponse
from app.services.ai_validation import (
    build_fallback_daily_plan_copy,
    build_fallback_lifestyle_analysis,
    coerce_daily_plan_copy_response,
    coerce_lifestyle_analysis_response,
    infer_lifestyle_types,
    parse_daily_plan_copy_input,
    parse_lifestyle_analysis_input,
    validate_lifestyle_analysis_response,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AI Client Exceptions
# ---------------------------------------------------------------------------


class AIClientError(Exception):
    """Raised when the AI service returns an error or produces an invalid response."""


class AITimeoutError(AIClientError):
    """Raised when the AI service does not respond within the configured timeout."""


class AIClient(Protocol):
    provider: str
    model_name: str
    prompt_version: str
    timeout_seconds: int

    def analyze_lifestyle(self, input_data: Dict[str, Any]) -> LifestyleAnalysisAIResponse:
        """Return AI-style lifestyle analysis without changing backend-calculated values."""

    def generate_daily_plan_copy(self, input_data: Dict[str, Any]) -> DailyPlanCopyAIResponse:
        """Return copy text for candidate actions without creating savings numbers."""


class MockAIClient:
    provider = "mock"
    model_name = "mock-ai-client"

    def __init__(self, prompt_version: Optional[str] = None, timeout_seconds: Optional[int] = None) -> None:
        self.prompt_version = prompt_version or settings.ai_prompt_version
        self.timeout_seconds = timeout_seconds or settings.ai_timeout_seconds

    def analyze_lifestyle(self, input_data: Dict[str, Any]) -> LifestyleAnalysisAIResponse:
        parsed_input = parse_lifestyle_analysis_input(input_data)
        primary_type, secondary_type = infer_lifestyle_types(parsed_input)
        raw_response = {
            "primary_type": primary_type,
            "secondary_type": secondary_type,
            "confidence": 0.84,
            "summary": _lifestyle_summary(primary_type, secondary_type),
            "reason": "프로필, 생활패턴 점수, 날씨 위험도를 기반으로 mock 분석 결과를 생성했습니다.",
        }
        return coerce_lifestyle_analysis_response(raw_response, input_data)

    def generate_daily_plan_copy(self, input_data: Dict[str, Any]) -> DailyPlanCopyAIResponse:
        parsed_input = parse_daily_plan_copy_input(input_data)
        raw_response = {
            "cheer_message": _cheer_message(parsed_input.lifestyle_analysis.primary_type if parsed_input.lifestyle_analysis else None),
            "actions": [
                _mock_action_copy(candidate.model_dump())
                for candidate in parsed_input.candidate_actions
            ],
        }
        return coerce_daily_plan_copy_response(raw_response, input_data)


class FallbackAIClient:
    provider = "fallback"
    model_name = "fallback-template"

    def __init__(self, prompt_version: Optional[str] = None, timeout_seconds: Optional[int] = None) -> None:
        self.prompt_version = prompt_version or settings.ai_prompt_version
        self.timeout_seconds = timeout_seconds or settings.ai_timeout_seconds

    def analyze_lifestyle(self, input_data: Dict[str, Any]) -> LifestyleAnalysisAIResponse:
        return build_fallback_lifestyle_analysis(input_data)

    def generate_daily_plan_copy(self, input_data: Dict[str, Any]) -> DailyPlanCopyAIResponse:
        return build_fallback_daily_plan_copy(input_data)


class BedrockAIClient:
    """AI client that calls AWS Bedrock for lifestyle analysis and recommendation copy."""

    provider = "bedrock"
    model_name = "anthropic.claude-3-haiku-20240307-v1:0"

    def __init__(
        self,
        prompt_version: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        model_id: Optional[str] = None,
        region_name: Optional[str] = None,
    ) -> None:
        self.prompt_version = prompt_version or settings.ai_prompt_version
        self.timeout_seconds = timeout_seconds or settings.ai_timeout_seconds
        self.model_name = model_id or self.model_name
        self._region_name = region_name or "ap-northeast-2"
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily initialise the Bedrock Runtime client with configured timeout."""
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config as BotoConfig
            except ImportError as exc:
                raise AIClientError(
                    "boto3 is required for BedrockAIClient. Install with: pip install boto3"
                ) from exc

            boto_config = BotoConfig(
                read_timeout=self.timeout_seconds,
                connect_timeout=5,
                retries={"max_attempts": 0},
            )
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self._region_name,
                config=boto_config,
            )
        return self._client

    def analyze_lifestyle(self, input_data: Dict[str, Any]) -> LifestyleAnalysisAIResponse:
        """Analyze lifestyle via AWS Bedrock. Raises AITimeoutError or AIClientError on failure."""
        prompt = self._build_lifestyle_prompt(input_data)

        try:
            raw_response = self._invoke_model(prompt)
        except AITimeoutError:
            raise
        except AIClientError:
            raise
        except Exception as exc:
            raise AIClientError(f"Unexpected error during Bedrock call: {exc}") from exc

        try:
            return validate_lifestyle_analysis_response(raw_response)
        except Exception as exc:
            raise AIClientError(f"AI response validation failed: {exc}") from exc

    def generate_daily_plan_copy(self, input_data: Dict[str, Any]) -> DailyPlanCopyAIResponse:
        """Generate recommendation copy via AWS Bedrock. Raises AITimeoutError or AIClientError."""
        prompt = self._build_daily_plan_prompt(input_data)

        try:
            raw_response = self._invoke_model(prompt)
        except AITimeoutError:
            raise
        except AIClientError:
            raise
        except Exception as exc:
            raise AIClientError(f"Unexpected error during Bedrock call: {exc}") from exc

        try:
            from app.services.ai_validation import validate_daily_plan_copy_response
            return validate_daily_plan_copy_response(raw_response, input_data)
        except Exception as exc:
            raise AIClientError(f"AI response validation failed: {exc}") from exc

    def _invoke_model(self, prompt: str) -> Dict[str, Any]:
        """Send prompt to Bedrock and parse the JSON response."""
        client = self._get_client()

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        })

        try:
            response = client.invoke_model(
                modelId=self.model_name,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
        except Exception as exc:
            error_name = type(exc).__name__
            # boto3 raises ReadTimeoutError or ClientError with timeout codes
            if "timeout" in error_name.lower() or "Timeout" in str(exc):
                raise AITimeoutError(
                    f"Bedrock request timed out after {self.timeout_seconds}s"
                ) from exc
            # Check for botocore-specific timeout exceptions
            try:
                from botocore.exceptions import ReadTimeoutError, ConnectTimeoutError
                if isinstance(exc, (ReadTimeoutError, ConnectTimeoutError)):
                    raise AITimeoutError(
                        f"Bedrock request timed out after {self.timeout_seconds}s"
                    ) from exc
            except ImportError:
                pass
            raise AIClientError(f"Bedrock invocation failed: {exc}") from exc

        try:
            response_body = json.loads(response["body"].read())
            # Extract text content from Claude response
            content_blocks = response_body.get("content", [])
            text_content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text_content += block.get("text", "")

            if not text_content:
                raise AIClientError("Bedrock response contained no text content")

            return json.loads(text_content)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AIClientError(f"Failed to parse Bedrock response: {exc}") from exc

    def _build_lifestyle_prompt(self, input_data: Dict[str, Any]) -> str:
        """Build a prompt for lifestyle analysis."""
        valid_types = [
            "아침형", "낮 활동형", "재택 체류형", "야간 활동형",
            "불규칙형", "외출 중심형", "냉방 고위험형", "절약 우선형",
        ]

        return f"""당신은 에너지 절약 전문 AI입니다. 사용자의 생활 데이터를 분석하여 생활유형을 판단해주세요.

## 입력 데이터
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 출력 형식
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

{{
  "primary_type": "8개 유형 중 하나",
  "secondary_type": "8개 유형 중 하나 또는 null",
  "confidence": 0.0~1.0 사이의 소수,
  "summary": "200자 이내의 분석 요약",
  "reason": "판단 근거 설명"
}}

## 유효한 생활유형 (8개)
{json.dumps(valid_types, ensure_ascii=False)}

## 규칙
- primary_type은 반드시 8개 유형 중 하나여야 합니다.
- secondary_type은 null이거나 8개 유형 중 하나여야 합니다 (primary_type과 다를 것).
- confidence는 0.0 이상 1.0 이하의 소수입니다.
- summary는 1자 이상 200자 이하여야 합니다.
- reason은 1자 이상이어야 합니다.
- JSON만 출력하세요. 코드 블록이나 설명 텍스트를 추가하지 마세요."""

    def _build_daily_plan_prompt(self, input_data: Dict[str, Any]) -> str:
        """Build a prompt for daily plan copy generation."""
        parsed = parse_daily_plan_copy_input(input_data)
        candidate_ids = [c.candidate_id for c in parsed.candidate_actions]

        return f"""당신은 에너지 절약 전문 AI입니다. 사용자 맞춤형 절약 행동 추천 문구를 생성해주세요.

## 입력 데이터
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 출력 형식
반드시 아래 JSON 형식으로만 응답하세요. 절약 금액은 계산하지 마세요.

{{
  "cheer_message": "응원 메시지 (1자 이상)",
  "actions": [
    {{
      "candidate_id": "입력의 candidate_id와 동일",
      "title": "행동 제목 (100자 이내)",
      "action": "구체적 행동 설명",
      "reason": "행동의 이유"
    }}
  ]
}}

## 규칙
- actions 배열에는 입력된 모든 candidate_id에 대한 항목이 있어야 합니다.
- 필요한 candidate_ids: {json.dumps(candidate_ids, ensure_ascii=False)}
- 절약 금액, kWh, CO₂ 값을 포함하지 마세요.
- JSON만 출력하세요."""


def get_ai_client(provider: Optional[str] = None) -> AIClient:
    selected_provider = (provider or settings.ai_provider).lower()
    if selected_provider == "mock":
        return MockAIClient()
    if selected_provider == "fallback":
        return FallbackAIClient()
    if selected_provider == "bedrock":
        return BedrockAIClient()

    return FallbackAIClient()


def _lifestyle_summary(primary_type: str, secondary_type: Optional[str]) -> str:
    if secondary_type:
        return f"{primary_type} 경향이 가장 강하고, {secondary_type} 특성도 함께 보여 오늘 행동 우선순위에 반영했습니다."
    return f"{primary_type} 경향이 가장 강하게 나타나 오늘 행동 우선순위에 반영했습니다."


def _cheer_message(primary_type: Optional[str]) -> str:
    if primary_type:
        return f"{primary_type} 패턴에 맞춰 오늘의 추천 행동을 준비했어요. 가능한 것부터 차근차근 실천해보세요."
    return "오늘의 추천 행동을 준비했어요. 가능한 것부터 차근차근 실천해보세요."


def _mock_action_copy(candidate: Dict[str, Any]) -> Dict[str, str]:
    action_type = str(candidate.get("action_type") or "general").lower()
    candidate_id = str(candidate.get("candidate_id"))
    time_range = candidate.get("time_range")
    evidence = candidate.get("evidence") or []
    evidence_text = ", ".join(str(item) for item in evidence[:3] if item)
    evidence_tail = f" {evidence_text} 조건을 고려했습니다." if evidence_text else ""

    if "shading" in action_type or "curtain" in action_type:
        return {
            "candidate_id": candidate_id,
            "title": "커튼으로 햇빛 차단하기",
            "action": _with_time(time_range, "커튼이나 블라인드를 닫아 직사광선을 막아주세요."),
            "reason": "실내로 들어오는 열을 줄이면 냉방 부담이 낮아집니다." + evidence_tail,
        }
    if "ventilation" in action_type:
        return {
            "candidate_id": candidate_id,
            "title": "시원한 시간대 환기하기",
            "action": _with_time(time_range, "창문을 열어 실내 열기를 먼저 빼주세요."),
            "reason": "실내에 쌓인 더운 공기를 빼면 냉방 시작 전 부담을 낮출 수 있습니다." + evidence_tail,
        }
    if "ac_temp" in action_type or "temperature" in action_type:
        return {
            "candidate_id": candidate_id,
            "title": "에어컨 설정온도 조정하기",
            "action": _with_time(time_range, "쾌적함을 해치지 않는 범위에서 설정온도를 조금 높여보세요."),
            "reason": "설정온도를 완만하게 조정하면 냉방 전력 사용을 줄이는 데 도움이 됩니다." + evidence_tail,
        }
    if "fan" in action_type:
        return {
            "candidate_id": candidate_id,
            "title": "선풍기로 냉기 순환하기",
            "action": _with_time(time_range, "선풍기를 함께 켜서 차가운 공기를 방 안에 고르게 퍼뜨려주세요."),
            "reason": "공기 순환이 좋아지면 같은 설정에서도 더 시원하게 느낄 수 있습니다." + evidence_tail,
        }

    return {
        "candidate_id": candidate_id,
        "title": candidate.get("title") or "추천 행동 실천하기",
        "action": candidate.get("action") or _with_time(time_range, "오늘 추천된 절약 행동을 실천해보세요."),
        "reason": candidate.get("reason") or "생활패턴과 날씨 조건을 바탕으로 실천 부담이 낮은 행동을 골랐습니다." + evidence_tail,
    }


def _with_time(time_range: Any, text: str) -> str:
    return f"{time_range}에 {text}" if time_range else text
