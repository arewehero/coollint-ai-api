from __future__ import annotations

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
)


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


def get_ai_client(provider: Optional[str] = None) -> AIClient:
    selected_provider = (provider or settings.ai_provider).lower()
    if selected_provider == "mock":
        return MockAIClient()
    if selected_provider == "fallback":
        return FallbackAIClient()

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
