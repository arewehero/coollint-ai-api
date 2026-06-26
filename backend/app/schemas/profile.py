from pydantic import BaseModel, Field
from typing import Literal


class HomeEnvironmentSchema(BaseModel):
    housing_type: Literal["원룸", "오피스텔", "아파트", "단독주택", "다세대"]
    direction: Literal["북향", "북동향", "동향", "남동향", "남향", "남서향", "서향", "북서향"]
    floor_level: Literal["반지하", "1층", "저층", "중층", "고층", "최상층"]
    building_age: Literal["신축", "보통", "노후"]
    insulation_level: Literal["좋음", "보통", "약함"]
    window_size: Literal["작음", "보통", "큼"]
    ventilation_level: Literal["잘됨", "보통", "잘 안됨"]
    window_sealing: Literal["잘 막힘", "보통", "틈새 있음"]


class LifestyleSchema(BaseModel):
    main_activity_time: Literal["아침형", "낮 활동", "야간 활동", "불규칙"]
    daytime_home_stay: Literal["거의 없음", "오후 잠깐", "오후 오래", "종일 재택"]
    sleep_time: Literal["밤", "새벽", "오전", "불규칙"]
    outdoor_activity: Literal["적음", "보통", "많음"]
    hot_time_home_stay: Literal["아니요", "가끔", "자주", "거의 항상"]


class EnergyProfileSchema(BaseModel):
    monthly_electricity_bill: int = Field(..., ge=0, le=1000000)
    monthly_goal_bill: int | None = Field(None, ge=0)
    comfort_preference: Literal["시원한 편 선호", "보통", "절약 우선"]
    ac_type: Literal["없음", "벽걸이", "스탠드", "둘 다"]
    has_fan: bool
    curtain_type: Literal["없음", "일반", "암막"]
    ac_power_watt: int | None = Field(None, gt=0, le=5000)
    room_size: Literal["~6평", "7~10평", "11~14평", "15평~"] | None = None
    current_temperature_setting: float | None = Field(None, ge=18, le=30)
    daily_ac_usage_hours: float | None = Field(None, ge=0, le=24)
    electricity_unit_price: float | None = Field(None, ge=1, le=1000)


class FullProfileRequest(BaseModel):
    home_environment: HomeEnvironmentSchema
    lifestyle: LifestyleSchema
    energy_profile: EnergyProfileSchema


class FullProfileResponse(BaseModel):
    home_environment: HomeEnvironmentSchema
    lifestyle: LifestyleSchema
    energy_profile: EnergyProfileSchema
