from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AIGenerationLog


def build_ai_generation_log(
    *,
    user_id: Optional[UUID],
    request_type: str,
    prompt_version: str,
    model_name: Optional[str],
    success: bool,
    latency_ms: Optional[int] = None,
    error_code: Optional[str] = None,
    request_payload: Optional[Mapping[str, Any]] = None,
    response_payload: Optional[Mapping[str, Any]] = None,
    log_payload: Optional[bool] = None,
) -> AIGenerationLog:
    should_log_payload = settings.ai_log_payload if log_payload is None else log_payload
    request_payload_dict = _mapping_to_dict(request_payload)
    response_payload_dict = _mapping_to_dict(response_payload)

    return AIGenerationLog(
        user_id=user_id,
        request_type=request_type,
        prompt_version=prompt_version,
        model_name=model_name,
        input_hash=hash_payload(request_payload_dict) if request_payload_dict else None,
        request_payload=request_payload_dict if should_log_payload else None,
        response_payload=response_payload_dict if should_log_payload else None,
        latency_ms=latency_ms,
        success=success,
        error_code=error_code,
    )


def record_ai_generation_log(
    db: Session,
    *,
    user_id: Optional[UUID],
    request_type: str,
    prompt_version: str,
    model_name: Optional[str],
    success: bool,
    latency_ms: Optional[int] = None,
    error_code: Optional[str] = None,
    request_payload: Optional[Mapping[str, Any]] = None,
    response_payload: Optional[Mapping[str, Any]] = None,
    log_payload: Optional[bool] = None,
    commit: bool = False,
) -> AIGenerationLog:
    log = build_ai_generation_log(
        user_id=user_id,
        request_type=request_type,
        prompt_version=prompt_version,
        model_name=model_name,
        success=success,
        latency_ms=latency_ms,
        error_code=error_code,
        request_payload=request_payload,
        response_payload=response_payload,
        log_payload=log_payload,
    )
    db.add(log)
    if commit:
        db.commit()
        db.refresh(log)
    return log


def hash_payload(payload: Mapping[str, Any]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _mapping_to_dict(payload: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    if payload is None:
        return None
    normalized = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, default=str)
    return json.loads(normalized)
