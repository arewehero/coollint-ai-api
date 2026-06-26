from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ValidationError

from app.schemas.ai import (
    CandidateActionInput,
    DailyPlanActionCopyAIResponse,
    DailyPlanCopyAIResponse,
    DailyPlanCopyInput,
    LifestyleAnalysisAIResponse,
    LifestyleAnalysisInput,
)


class AIResponseValidationError(ValueError):
    """Raised when an AI response does not match the backend contract."""


def validate_lifestyle_analysis_response(raw_response: Any) -> LifestyleAnalysisAIResponse:
    try:
        return LifestyleAnalysisAIResponse.model_validate(raw_response)
    except ValidationError as exc:
        raise AIResponseValidationError("Invalid lifestyle analysis AI response") from exc


def validate_daily_plan_copy_response(raw_response: Any, input_data: Any) -> DailyPlanCopyAIResponse:
    try:
        response = DailyPlanCopyAIResponse.model_validate(raw_response)
    except ValidationError as exc:
        raise AIResponseValidationError("Invalid daily plan copy AI response") from exc

    expected_ids = [candidate.candidate_id for candidate in parse_daily_plan_copy_input(input_data).candidate_actions]
    if not expected_ids:
        return response

    actual_ids = [action.candidate_id for action in response.actions]
    if len(actual_ids) != len(set(actual_ids)):
        raise AIResponseValidationError("Daily plan copy AI response contains duplicate candidate_id values")

    missing_ids = set(expected_ids) - set(actual_ids)
    unexpected_ids = set(actual_ids) - set(expected_ids)
    if missing_ids or unexpected_ids:
        raise AIResponseValidationError("Daily plan copy AI response candidate_id values do not match input")

    actions_by_id = {action.candidate_id: action for action in response.actions}
    return DailyPlanCopyAIResponse(
        cheer_message=response.cheer_message,
        actions=[actions_by_id[candidate_id] for candidate_id in expected_ids],
    )


def coerce_lifestyle_analysis_response(raw_response: Any, input_data: Any) -> LifestyleAnalysisAIResponse:
    try:
        return validate_lifestyle_analysis_response(raw_response)
    except AIResponseValidationError:
        return build_fallback_lifestyle_analysis(input_data)


def coerce_daily_plan_copy_response(raw_response: Any, input_data: Any) -> DailyPlanCopyAIResponse:
    try:
        return validate_daily_plan_copy_response(raw_response, input_data)
    except AIResponseValidationError:
        return build_fallback_daily_plan_copy(input_data)


def parse_lifestyle_analysis_input(input_data: Any) -> LifestyleAnalysisInput:
    return LifestyleAnalysisInput.model_validate(_to_mapping(input_data))


def parse_daily_plan_copy_input(input_data: Any) -> DailyPlanCopyInput:
    return DailyPlanCopyInput.model_validate(_to_mapping(input_data))


def build_fallback_lifestyle_analysis(input_data: Any) -> LifestyleAnalysisAIResponse:
    parsed_input = parse_lifestyle_analysis_input(input_data)
    primary_type, secondary_type = infer_lifestyle_types(parsed_input)

    return LifestyleAnalysisAIResponse(
        primary_type=primary_type,
        secondary_type=secondary_type,
        confidence=0.62,
        summary=f"{primary_type} 특성을 기준으로 오늘 실천하기 쉬운 절약 행동을 우선 추천합니다.",
        reason="AI 응답을 사용할 수 없어 백엔드 점수와 프로필 기반 fallback 규칙을 적용했습니다.",
    )


def build_fallback_daily_plan_copy(input_data: Any) -> DailyPlanCopyAIResponse:
    candidates = _extract_candidate_actions(input_data)
    actions = [build_fallback_action_copy(candidate) for candidate in candidates]

    return DailyPlanCopyAIResponse(
        cheer_message="오늘 추천 행동을 하나씩 실천해 보세요. 작은 조정만으로도 전기 사용을 줄이는 데 도움이 됩니다.",
        actions=actions,
    )


def build_fallback_action_copy(candidate: CandidateActionInput) -> DailyPlanActionCopyAIResponse:
    title, action, reason = _copy_template_for(candidate)
    return DailyPlanActionCopyAIResponse(
        candidate_id=candidate.candidate_id,
        title=candidate.title or title,
        action=candidate.action or action,
        reason=candidate.reason or reason,
    )


def infer_lifestyle_types(input_data: LifestyleAnalysisInput) -> Tuple[str, Optional[str]]:
    scores = input_data.scores or {}
    score_candidates = [
        ("morning_score", "아침형"),
        ("daytime_score", "낮 활동형"),
        ("night_score", "야간 활동형"),
        ("irregular_score", "불규칙형"),
        ("stay_home_score", "재택 체류형"),
        ("outing_score", "외출 중심형"),
        ("cooling_need_score", "냉방 고위험형"),
        ("saving_priority_score", "절약 우선형"),
    ]

    ranked = sorted(
        ((int(scores.get(key, 0) or 0), label) for key, label in score_candidates),
        reverse=True,
    )
    positive_ranked = [(score, label) for score, label in ranked if score > 0]
    if not positive_ranked:
        return _type_from_profile(input_data.profile), "절약 우선형"

    primary_type = positive_ranked[0][1]
    secondary_type = next((label for _, label in positive_ranked[1:] if label != primary_type), None)
    return primary_type, secondary_type


def _type_from_profile(profile: Mapping[str, Any]) -> str:
    lifestyle = profile.get("lifestyle", {}) if isinstance(profile, Mapping) else {}
    main_activity_time = lifestyle.get("main_activity_time") if isinstance(lifestyle, Mapping) else None
    mapping = {
        "아침형": "아침형",
        "낮 활동": "낮 활동형",
        "야간 활동": "야간 활동형",
        "불규칙": "불규칙형",
    }
    return mapping.get(main_activity_time, "절약 우선형")


def _extract_candidate_actions(input_data: Any) -> List[CandidateActionInput]:
    try:
        return parse_daily_plan_copy_input(input_data).candidate_actions
    except ValidationError:
        raw_input = _to_mapping(input_data)
        raw_candidates = raw_input.get("candidate_actions", [])
        if not isinstance(raw_candidates, Iterable) or isinstance(raw_candidates, (str, bytes)):
            return []

        candidates = []
        for index, raw_candidate in enumerate(raw_candidates, start=1):
            raw = raw_candidate if isinstance(raw_candidate, Mapping) else {}
            candidate_id = str(raw.get("candidate_id") or f"candidate_{index:03d}")
            candidates.append(
                CandidateActionInput(
                    candidate_id=candidate_id,
                    action_type=str(raw.get("action_type") or "general"),
                    time_range=_optional_string(raw.get("time_range")),
                    title=_optional_string(raw.get("title")),
                    action=_optional_string(raw.get("action")),
                    reason=_optional_string(raw.get("reason")),
                    difficulty=_optional_string(raw.get("difficulty")),
                    evidence=[str(item) for item in raw.get("evidence", []) if item is not None]
                    if isinstance(raw.get("evidence", []), list)
                    else [],
                )
            )
        return candidates


def _copy_template_for(candidate: CandidateActionInput) -> Tuple[str, str, str]:
    action_type = candidate.action_type.lower()
    time_prefix = f"{candidate.time_range}에 " if candidate.time_range else ""
    evidence = ", ".join(candidate.evidence[:3])
    evidence_reason = f" 입력 조건({evidence})을 반영했습니다." if evidence else ""

    if "ventilation" in action_type or "환기" in action_type:
        return (
            "시원한 시간대 환기하기",
            f"{time_prefix}창문을 열어 실내 열기를 먼저 빼주세요.",
            "바깥 공기가 비교적 시원한 시간에 환기하면 냉방 부담을 줄일 수 있습니다." + evidence_reason,
        )
    if "shading" in action_type or "curtain" in action_type or "차광" in action_type:
        return (
            "햇빛 들어오기 전에 차광하기",
            f"{time_prefix}커튼이나 블라인드로 직사광선을 막아주세요.",
            "햇빛 유입을 줄이면 실내 온도 상승을 늦출 수 있습니다." + evidence_reason,
        )
    if "ac_temp" in action_type or "temperature" in action_type or "에어컨" in action_type:
        return (
            "에어컨 설정온도 조정하기",
            f"{time_prefix}무리 없는 범위에서 에어컨 설정온도를 조금 높여보세요.",
            "설정온도를 완만하게 조정하면 쾌적함을 유지하면서 냉방 전력 사용을 줄일 수 있습니다." + evidence_reason,
        )
    if "fan" in action_type or "선풍기" in action_type:
        return (
            "선풍기 함께 사용하기",
            f"{time_prefix}에어컨 바람이 퍼지도록 선풍기를 함께 사용해보세요.",
            "공기 순환을 만들면 같은 설정에서도 더 시원하게 느낄 수 있습니다." + evidence_reason,
        )
    return (
        "추천 행동 실천하기",
        f"{time_prefix}오늘의 추천 행동을 가능한 범위에서 실천해보세요.",
        "사용자 입력과 날씨 조건을 바탕으로 실천 부담이 낮은 행동을 우선 제안했습니다." + evidence_reason,
    )


def _to_mapping(input_data: Any) -> Dict[str, Any]:
    if isinstance(input_data, BaseModel):
        return input_data.model_dump()
    if isinstance(input_data, Mapping):
        return dict(input_data)
    return {}


def _optional_string(value: Any) -> Optional[str]:
    return str(value) if value is not None else None
