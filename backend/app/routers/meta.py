from fastapi import APIRouter, Request

from app.schemas.common import SuccessResponse

router = APIRouter()


@router.get("/enums", response_model=SuccessResponse)
async def get_enums(request: Request):
    """프론트 입력 폼 구성을 위한 선택지 조회."""
    data = {
        "housing_types": ["원룸", "오피스텔", "아파트", "단독주택", "다세대"],
        "directions": ["북향", "북동향", "동향", "남동향", "남향", "남서향", "서향", "북서향"],
        "floor_levels": ["반지하", "1층", "저층", "중층", "고층", "최상층"],
        "building_ages": ["신축", "보통", "노후"],
        "insulation_levels": ["좋음", "보통", "약함"],
        "window_sizes": ["작음", "보통", "큼"],
        "ventilation_levels": ["잘됨", "보통", "잘 안됨"],
        "window_sealings": ["잘 막힘", "보통", "틈새 있음"],
        "main_activity_times": ["아침형", "낮 활동", "야간 활동", "불규칙"],
        "daytime_home_stays": ["거의 없음", "오후 잠깐", "오후 오래", "종일 재택"],
        "sleep_times": ["밤", "새벽", "오전", "불규칙"],
        "outdoor_activities": ["적음", "보통", "많음"],
        "hot_time_home_stays": ["아니요", "가끔", "자주", "거의 항상"],
        "ac_types": ["없음", "벽걸이", "스탠드", "둘 다"],
        "curtain_types": ["없음", "일반", "암막"],
        "room_sizes": ["~6평", "7~10평", "11~14평", "15평~"],
        "comfort_preferences": ["시원한 편 선호", "보통", "절약 우선"],
        "difficulties": ["쉬움", "보통", "어려움"],
    }
    return SuccessResponse(data=data, meta={"request_id": request.state.request_id})


@router.get("/assumptions", response_model=SuccessResponse)
async def get_assumptions(request: Request):
    """계산 기준값 조회."""
    data = {
        "co2_factor_kg_per_kwh": 0.4781,
        "default_electricity_unit_price": 150,
        "tree_absorption_kg_per_year": 6.6,
        "temperature_coefficients": {
            "26": 0.92,
            "25": 1.0,
            "24": 1.08,
            "23": 1.17,
        },
    }
    return SuccessResponse(data=data, meta={"request_id": request.state.request_id})
