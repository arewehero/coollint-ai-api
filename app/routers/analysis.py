"""Analysis router — score calculation and lifestyle analysis endpoints.

POST /api/v1/analysis/scores calculates 12 lifestyle/home scores,
upserts a ScoreSnapshot, and returns the result.

POST /api/v1/ai/lifestyle-analysis performs AI-based lifestyle type analysis,
validates and saves the result, or falls back to score-based rules.

Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 5.1, 5.2, 5.3, 5.5, 5.6, 5.7
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import ApiException, ErrorCode, api_meta_from_request
from app.core.security import get_current_user_id
from app.core.time_utils import get_kst_today, parse_date
from app.db.session import get_db
from app.models.recommendation import LifestyleAnalysis
from app.repositories.profile_repository import ProfileRepository
from app.repositories.score_repository import ScoreRepository
from app.schemas.analysis import LifestyleAnalysisResponse
from app.schemas.common import ApiSuccessResponse
from app.schemas.score import ScoreCalculationRequest, ScoreSnapshotResponse
from app.services.ai_client import AIClient, AIClientError, AITimeoutError, get_ai_client
from app.services.ai_logging import record_ai_generation_log
from app.services.scoring_service import calculate_all_scores
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


def get_profile_repository() -> ProfileRepository:
    return ProfileRepository()


def get_score_repository() -> ScoreRepository:
    return ScoreRepository()


def get_weather_service() -> WeatherService:
    return WeatherService()


@router.post(
    "/scores",
    response_model=ApiSuccessResponse[ScoreSnapshotResponse],
    summary="점수 계산",
    description="사용자 프로필 기반 12개 점수를 계산하고 ScoreSnapshot을 저장합니다.",
)
def calculate_scores(
    request: Request,
    body: ScoreCalculationRequest,
    user_id=Depends(get_current_user_id),
    db: Session = Depends(get_db),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
    score_repo: ScoreRepository = Depends(get_score_repository),
    weather_service: WeatherService = Depends(get_weather_service),
) -> ApiSuccessResponse[ScoreSnapshotResponse]:
    """Calculate all 12 scores and upsert a ScoreSnapshot.

    Flow:
    1. Parse optional date (defaults to today KST) — Req 11.2
    2. Get profile → if None, raise PROFILE_REQUIRED — Req 4.5
    3. Get weather for that date (optional, don't fail) — Req 12.1
    4. Calculate all 12 scores via calculate_all_scores() — Req 4.1, 4.2
    5. Upsert ScoreSnapshot — Req 4.3, 4.6
    6. Return ScoreSnapshotResponse
    """
    # 1. Parse date (defaults to today KST)
    target_date = body.date if body.date is not None else get_kst_today()

    # 2. Get profile — raise 422 PROFILE_REQUIRED if not registered
    profile = profile_repo.get_profile(db, user_id)
    if profile is None:
        raise ApiException.from_error_code(ErrorCode.PROFILE_REQUIRED)

    # 3. Get weather (optional — don't fail if unavailable)
    weather_data: Optional[dict] = None
    try:
        weather_response = weather_service.get_hourly_weather(db, date=target_date)
        # Extract morning_temp and rain from time blocks for scoring
        weather_data = _extract_weather_for_scoring(weather_response)
    except Exception as e:
        logger.warning(f"Weather data unavailable for scoring, using None: {e}")
        weather_data = None

    # 4. Calculate all 12 scores
    lifestyle = profile.get("lifestyle", {})
    home_env = profile.get("home_environment", {})
    energy = profile.get("energy_profile", {})

    scores = calculate_all_scores(
        lifestyle=lifestyle,
        home_env=home_env,
        energy=energy,
        weather=weather_data,
    )

    # 5. Upsert ScoreSnapshot
    snapshot = score_repo.upsert_score_snapshot(db, user_id, target_date, scores)
    db.commit()
    db.refresh(snapshot)

    # 6. Return response
    response_data = ScoreSnapshotResponse.model_validate(snapshot)
    # Include dominant_signals from the calculated scores
    response_data.dominant_signals = scores.get("dominant_signals", [])

    return ApiSuccessResponse(
        data=response_data,
        meta=api_meta_from_request(request),
    )


def _extract_weather_for_scoring(weather_response) -> Optional[dict]:
    """Extract morning_temp and rain from WeatherHourlyResponse for scoring.

    The scoring service expects:
    - morning_temp: float (오전 기온)
    - rain: bool (강수 여부)
    """
    if weather_response is None or not hasattr(weather_response, "time_blocks"):
        return None

    morning_temp = None
    rain = False

    for block in weather_response.time_blocks:
        # Use 아침 (morning) time block for temperature
        if block.time_range == "아침":
            morning_temp = block.temperature
            rain = rain or block.rain
        # Also consider 오전 if 아침 is not available
        elif block.time_range == "오전" and morning_temp is None:
            morning_temp = block.temperature
            rain = rain or block.rain

    if morning_temp is None:
        return None

    return {"morning_temp": morning_temp, "rain": rain}


# ---------------------------------------------------------------------------
# Lifestyle Analysis Endpoint (Requirements 5.1, 5.2, 5.3, 5.5, 5.6, 5.7)
# ---------------------------------------------------------------------------

# Score-to-type mapping for fallback logic
SCORE_TO_TYPE = {
    "morning_score": "아침형",
    "daytime_score": "낮 활동형",
    "stay_home_score": "재택 체류형",
    "night_score": "야간 활동형",
    "irregular_score": "불규칙형",
    "outing_score": "외출 중심형",
    "cooling_need_score": "냉방 고위험형",
    "saving_priority_score": "절약 우선형",
}


def fallback_lifestyle_type(scores: dict) -> str:
    """Determine primary_type from score snapshot using max-score rule.

    Finds the score key with the highest value and maps it to a lifestyle type.
    Defaults to '불규칙형' if no mapping found or scores are empty.

    Requirements: 5.5
    """
    relevant_scores = {k: v for k, v in scores.items() if k in SCORE_TO_TYPE}
    if not relevant_scores:
        return "불규칙형"

    max_score_key = max(relevant_scores, key=relevant_scores.get)
    return SCORE_TO_TYPE.get(max_score_key, "불규칙형")


def get_ai_client_for_analysis() -> AIClient:
    """Get AI client for lifestyle analysis."""
    return get_ai_client()


def perform_lifestyle_analysis(
    *,
    user_id,
    target_date,
    db: Session,
    profile_repo: ProfileRepository,
    score_repo: ScoreRepository,
    ai_client: AIClient,
) -> LifestyleAnalysis:
    """Core lifestyle analysis logic: profile+score check → AI call → validate → save/fallback.

    Flow:
    1. Check profile exists → 422 PROFILE_REQUIRED if not — Req 5.1
    2. Check ScoreSnapshot exists for (user_id, date) → 422 PREREQUISITE_MISSING — Req 5.1
    3. Build AI input → call AI → validate response — Req 5.1, 5.2, 5.3
    4. If AI fails or validation fails, use fallback — Req 5.5
    5. Upsert LifestyleAnalysis in DB — Req 5.6, 5.7
    6. Return LifestyleAnalysis ORM instance

    Requirements: 5.1, 5.2, 5.3, 5.5, 5.6, 5.7
    """
    # 1. Check profile exists
    profile = profile_repo.get_profile(db, user_id)
    if profile is None:
        raise ApiException.from_error_code(ErrorCode.PROFILE_REQUIRED)

    # 2. Check ScoreSnapshot exists
    snapshot = score_repo.get_score_snapshot(db, user_id, target_date)
    if snapshot is None:
        raise ApiException.from_error_code(
            ErrorCode.PREREQUISITE_MISSING,
            message="점수 계산이 선행되어야 합니다. 먼저 POST /api/v1/analysis/scores를 호출해주세요.",
            details={"missing": "score_snapshot", "user_id": str(user_id), "date": str(target_date)},
        )

    # 4. Build AI input payload
    scores_dict = {
        "morning_score": snapshot.morning_score,
        "daytime_score": snapshot.daytime_score,
        "night_score": snapshot.night_score,
        "irregular_score": snapshot.irregular_score,
        "stay_home_score": snapshot.stay_home_score,
        "outing_score": snapshot.outing_score,
        "cooling_need_score": snapshot.cooling_need_score,
        "saving_priority_score": snapshot.saving_priority_score,
        "saving_opportunity_score": snapshot.saving_opportunity_score,
        "heat_gain_score": snapshot.heat_gain_score,
        "cooling_loss_score": snapshot.cooling_loss_score,
        "ventilation_score": snapshot.ventilation_score,
    }

    ai_input = {
        "user_id": str(user_id),
        "date": str(target_date),
        "profile": profile,
        "scores": scores_dict,
    }

    # 5. Call AI → validate → fallback if needed
    ai_response = None
    used_fallback = False
    model_name = ai_client.model_name
    prompt_version = ai_client.prompt_version
    error_code_str = None
    latency_ms = None

    start_time = time.time()
    try:
        ai_response = ai_client.analyze_lifestyle(ai_input)
        latency_ms = int((time.time() - start_time) * 1000)
    except AITimeoutError as exc:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"AI lifestyle analysis timed out for user {user_id}: {exc}")
        error_code_str = "AI_TIMEOUT"
        used_fallback = True
    except (AIClientError, Exception) as exc:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"AI lifestyle analysis failed for user {user_id}: {exc}")
        error_code_str = "AI_CLIENT_ERROR"
        used_fallback = True

    # Validate AI response if we got one
    if ai_response is not None and not used_fallback:
        # Additional validation: check primary_type is in allowed set
        allowed_types = [
            "아침형", "낮 활동형", "재택 체류형", "야간 활동형",
            "불규칙형", "외출 중심형", "냉방 고위험형", "절약 우선형",
        ]
        if ai_response.primary_type not in allowed_types:
            logger.warning(
                f"AI returned invalid primary_type '{ai_response.primary_type}' for user {user_id}"
            )
            error_code_str = "AI_VALIDATION_FAILED"
            used_fallback = True
            ai_response = None

    # Apply fallback if needed
    if used_fallback or ai_response is None:
        primary_type = fallback_lifestyle_type(scores_dict)
        # Determine secondary type from second-highest score
        secondary_type = _get_secondary_type(scores_dict, primary_type)
        model_name = "fallback-rule"
        prompt_version = "fallback"

        ai_response_data = {
            "primary_type": primary_type,
            "secondary_type": secondary_type,
            "confidence": 0.6,
            "summary": f"{primary_type} 특성을 기준으로 절약 행동을 우선 추천합니다.",
            "reason": "AI 분석 불가로 점수 기반 규칙을 적용했습니다.",
        }
    else:
        ai_response_data = {
            "primary_type": ai_response.primary_type,
            "secondary_type": ai_response.secondary_type,
            "confidence": ai_response.confidence,
            "summary": ai_response.summary,
            "reason": ai_response.reason,
        }

    # 6. Record AI generation log
    record_ai_generation_log(
        db,
        user_id=user_id,
        request_type="lifestyle_analysis",
        prompt_version=prompt_version,
        model_name=model_name,
        success=not used_fallback,
        latency_ms=latency_ms,
        error_code=error_code_str,
        request_payload=ai_input,
        response_payload=ai_response_data if not used_fallback else None,
    )

    # 7. Upsert LifestyleAnalysis in DB (Req 5.6, 5.7)
    existing_analysis = (
        db.query(LifestyleAnalysis)
        .filter(
            LifestyleAnalysis.user_id == user_id,
            LifestyleAnalysis.date == target_date,
        )
        .first()
    )

    raw_response_json = ai_response_data if not used_fallback else {
        "fallback": True, **ai_response_data
    }

    if existing_analysis:
        existing_analysis.primary_type = ai_response_data["primary_type"]
        existing_analysis.secondary_type = ai_response_data["secondary_type"]
        existing_analysis.confidence = ai_response_data["confidence"]
        existing_analysis.summary = ai_response_data["summary"]
        existing_analysis.reason = ai_response_data.get("reason")
        existing_analysis.model_name = model_name
        existing_analysis.prompt_version = prompt_version
        existing_analysis.raw_ai_response = raw_response_json
        db.flush()
        analysis = existing_analysis
    else:
        analysis = LifestyleAnalysis(
            user_id=user_id,
            date=target_date,
            primary_type=ai_response_data["primary_type"],
            secondary_type=ai_response_data["secondary_type"],
            confidence=ai_response_data["confidence"],
            summary=ai_response_data["summary"],
            reason=ai_response_data.get("reason"),
            model_name=model_name,
            prompt_version=prompt_version,
            raw_ai_response=raw_response_json,
        )
        db.add(analysis)
        db.flush()

    db.commit()
    db.refresh(analysis)

    return analysis


def _get_secondary_type(scores_dict: dict, primary_type: str) -> Optional[str]:
    """Get the secondary lifestyle type (second highest score, different from primary)."""
    relevant_scores = {k: v for k, v in scores_dict.items() if k in SCORE_TO_TYPE}
    if not relevant_scores:
        return None

    sorted_scores = sorted(relevant_scores.items(), key=lambda x: x[1], reverse=True)
    for key, value in sorted_scores:
        mapped_type = SCORE_TO_TYPE[key]
        if mapped_type != primary_type and value > 0:
            return mapped_type
    return None
