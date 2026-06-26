"""AI 응답 JSON Schema 검증 서비스. (담당: AI 담당자 + 임혜성)"""
import json
from typing import Any


LIFESTYLE_TYPES = ["아침형", "낮 활동형", "재택 체류형", "야간 활동형", "불규칙형", "외출 중심형", "냉방 고위험형", "절약 우선형"]


def validate_lifestyle_analysis(response: dict[str, Any]) -> bool:
    """생활 유형 판단 AI 응답을 검증한다."""
    analysis = response.get("lifestyle_analysis")
    if not analysis:
        return False
    if analysis.get("primary_type") not in LIFESTYLE_TYPES:
        return False
    st = analysis.get("secondary_type")
    if st is not None and st not in LIFESTYLE_TYPES:
        return False
    confidence = analysis.get("confidence", -1)
    if not (0 <= confidence <= 1):
        return False
    if not analysis.get("summary") or len(analysis["summary"]) > 200:
        return False
    return True


def validate_daily_plan_copy(response: dict[str, Any], candidate_ids: list[str]) -> bool:
    """추천 문구 AI 응답을 검증한다."""
    daily_summary = response.get("daily_summary")
    if not daily_summary or not daily_summary.get("cheer_message"):
        return False
    if len(daily_summary["cheer_message"]) > 250:
        return False

    recommendations = response.get("recommendations", [])
    if not recommendations:
        return False

    for rec in recommendations:
        if rec.get("candidate_id") not in candidate_ids:
            return False
        if not rec.get("title") or len(rec["title"]) > 30:
            return False
        if not rec.get("action") or len(rec["action"]) > 120:
            return False
        if not rec.get("reason") or len(rec["reason"]) > 200:
            return False

    return True
