"""AI Response Validation Service.

Provides simple boolean-returning validation functions for AI responses.
Caller should switch to fallback logic when validation returns False.

Requirements: 10.1, 10.2
"""

from __future__ import annotations

from typing import Any, Dict

# 8 valid lifestyle types defined in the design document
VALID_LIFESTYLE_TYPES: list[str] = [
    "아침형",
    "낮 활동형",
    "재택 체류형",
    "야간 활동형",
    "불규칙형",
    "외출 중심형",
    "냉방 고위험형",
    "절약 우선형",
]


def validate_lifestyle_analysis(response: dict) -> bool:
    """Validate AI lifestyle analysis response.

    Returns True if all fields are valid, False otherwise.
    Caller should switch to fallback logic on False.

    Validation rules:
    - primary_type: must be one of the 8 valid lifestyle types
    - secondary_type: must be None or one of the 8 valid lifestyle types
    - confidence: must be a number in [0.0, 1.0]
    - summary: must be a string with length 1-200
    """
    if not isinstance(response, dict):
        return False

    # 1. primary_type validation
    primary_type = response.get("primary_type")
    if primary_type not in VALID_LIFESTYLE_TYPES:
        return False

    # 2. secondary_type validation (None is allowed)
    secondary_type = response.get("secondary_type")
    if secondary_type is not None and secondary_type not in VALID_LIFESTYLE_TYPES:
        return False

    # 3. confidence validation: number in [0.0, 1.0]
    confidence = response.get("confidence")
    if not isinstance(confidence, (int, float)):
        return False
    if confidence < 0.0 or confidence > 1.0:
        return False

    # 4. summary validation: string with length 1-200
    summary = response.get("summary")
    if not isinstance(summary, str):
        return False
    if len(summary) < 1 or len(summary) > 200:
        return False

    return True


def validate_recommendation_copy(response: dict) -> bool:
    """Validate AI recommendation copy response.

    Returns True if all fields are valid, False otherwise.
    Caller should switch to fallback logic on False.

    Validation rules:
    - title: non-empty string
    - action: non-empty string (description)
    - reason: non-empty string
    - cheer_message: non-empty string (if present)
    """
    if not isinstance(response, dict):
        return False

    # 1. title validation: non-empty string
    title = response.get("title")
    if not isinstance(title, str) or len(title) == 0:
        return False

    # 2. action validation: non-empty string
    action = response.get("action")
    if not isinstance(action, str) or len(action) == 0:
        return False

    # 3. reason validation: non-empty string
    reason = response.get("reason")
    if not isinstance(reason, str) or len(reason) == 0:
        return False

    # 4. cheer_message validation: non-empty string if present
    cheer_message = response.get("cheer_message")
    if cheer_message is not None:
        if not isinstance(cheer_message, str) or len(cheer_message) == 0:
            return False

    return True
