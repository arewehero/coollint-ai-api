"""프로필 스키마 검증 테스트 (Task 2.1: 프로필 스키마 보강)

Validates: Requirements 2.2, 2.3, 2.4, 2.5, 2.6
"""
import pytest
from pydantic import ValidationError

from app.schemas.profile import (
    EnergyProfileSchema,
    FullProfileRequest,
    FullProfileResponse,
    HomeEnvironmentSchema,
    LifestyleSchema,
)


# --- Valid sample data ---

VALID_HOME_ENVIRONMENT = {
    "housing_type": "아파트",
    "direction": "남향",
    "floor_level": "중층",
    "building_age": "보통",
    "insulation_level": "보통",
    "window_size": "보통",
    "ventilation_level": "보통",
    "window_sealing": "보통",
}

VALID_LIFESTYLE = {
    "main_activity_time": "아침형",
    "daytime_home_stay": "거의 없음",
    "sleep_time": "밤",
    "outdoor_activity": "보통",
    "hot_time_home_stay": "가끔",
}

VALID_ENERGY_PROFILE = {
    "monthly_electricity_bill": 50000,
    "monthly_goal_bill": 40000,
    "comfort_preference": "보통",
    "ac_type": "벽걸이",
    "has_fan": True,
    "curtain_type": "일반",
}


class TestHomeEnvironmentSchema:
    """Req 2.2: HomeEnvironment 필드 검증."""

    def test_valid_all_values(self):
        """모든 유효한 Literal 값이 허용됨."""
        schema = HomeEnvironmentSchema(**VALID_HOME_ENVIRONMENT)
        assert schema.housing_type == "아파트"
        assert schema.direction == "남향"

    @pytest.mark.parametrize("housing_type", ["원룸", "오피스텔", "아파트", "단독주택", "다세대"])
    def test_valid_housing_types(self, housing_type):
        data = {**VALID_HOME_ENVIRONMENT, "housing_type": housing_type}
        schema = HomeEnvironmentSchema(**data)
        assert schema.housing_type == housing_type

    @pytest.mark.parametrize("direction", ["북향", "북동향", "동향", "남동향", "남향", "남서향", "서향", "북서향"])
    def test_valid_directions(self, direction):
        data = {**VALID_HOME_ENVIRONMENT, "direction": direction}
        schema = HomeEnvironmentSchema(**data)
        assert schema.direction == direction

    @pytest.mark.parametrize("floor_level", ["반지하", "1층", "저층", "중층", "고층", "최상층"])
    def test_valid_floor_levels(self, floor_level):
        data = {**VALID_HOME_ENVIRONMENT, "floor_level": floor_level}
        schema = HomeEnvironmentSchema(**data)
        assert schema.floor_level == floor_level

    @pytest.mark.parametrize("building_age", ["신축", "보통", "노후"])
    def test_valid_building_ages(self, building_age):
        data = {**VALID_HOME_ENVIRONMENT, "building_age": building_age}
        schema = HomeEnvironmentSchema(**data)
        assert schema.building_age == building_age

    @pytest.mark.parametrize("insulation_level", ["좋음", "보통", "약함"])
    def test_valid_insulation_levels(self, insulation_level):
        data = {**VALID_HOME_ENVIRONMENT, "insulation_level": insulation_level}
        schema = HomeEnvironmentSchema(**data)
        assert schema.insulation_level == insulation_level

    @pytest.mark.parametrize("window_size", ["작음", "보통", "큼"])
    def test_valid_window_sizes(self, window_size):
        data = {**VALID_HOME_ENVIRONMENT, "window_size": window_size}
        schema = HomeEnvironmentSchema(**data)
        assert schema.window_size == window_size

    @pytest.mark.parametrize("ventilation_level", ["잘됨", "보통", "잘 안됨"])
    def test_valid_ventilation_levels(self, ventilation_level):
        data = {**VALID_HOME_ENVIRONMENT, "ventilation_level": ventilation_level}
        schema = HomeEnvironmentSchema(**data)
        assert schema.ventilation_level == ventilation_level

    @pytest.mark.parametrize("window_sealing", ["잘 막힘", "보통", "틈새 있음"])
    def test_valid_window_sealings(self, window_sealing):
        data = {**VALID_HOME_ENVIRONMENT, "window_sealing": window_sealing}
        schema = HomeEnvironmentSchema(**data)
        assert schema.window_sealing == window_sealing

    def test_invalid_housing_type_returns_422(self):
        """Req 2.5: 유효하지 않은 값 → ValidationError."""
        data = {**VALID_HOME_ENVIRONMENT, "housing_type": "빌라"}
        with pytest.raises(ValidationError) as exc_info:
            HomeEnvironmentSchema(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("housing_type",) for e in errors)

    def test_invalid_direction_returns_422(self):
        data = {**VALID_HOME_ENVIRONMENT, "direction": "동남향"}
        with pytest.raises(ValidationError) as exc_info:
            HomeEnvironmentSchema(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("direction",) for e in errors)

    def test_missing_field_returns_422(self):
        data = {k: v for k, v in VALID_HOME_ENVIRONMENT.items() if k != "housing_type"}
        with pytest.raises(ValidationError) as exc_info:
            HomeEnvironmentSchema(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("housing_type",) for e in errors)


class TestLifestyleSchema:
    """Req 2.3: Lifestyle 필드 검증."""

    def test_valid_all_values(self):
        schema = LifestyleSchema(**VALID_LIFESTYLE)
        assert schema.main_activity_time == "아침형"

    @pytest.mark.parametrize("main_activity_time", ["아침형", "낮 활동", "야간 활동", "불규칙"])
    def test_valid_main_activity_times(self, main_activity_time):
        data = {**VALID_LIFESTYLE, "main_activity_time": main_activity_time}
        schema = LifestyleSchema(**data)
        assert schema.main_activity_time == main_activity_time

    @pytest.mark.parametrize("daytime_home_stay", ["거의 없음", "오후 잠깐", "오후 오래", "종일 재택"])
    def test_valid_daytime_home_stays(self, daytime_home_stay):
        data = {**VALID_LIFESTYLE, "daytime_home_stay": daytime_home_stay}
        schema = LifestyleSchema(**data)
        assert schema.daytime_home_stay == daytime_home_stay

    @pytest.mark.parametrize("sleep_time", ["밤", "새벽", "오전", "불규칙"])
    def test_valid_sleep_times(self, sleep_time):
        data = {**VALID_LIFESTYLE, "sleep_time": sleep_time}
        schema = LifestyleSchema(**data)
        assert schema.sleep_time == sleep_time

    @pytest.mark.parametrize("outdoor_activity", ["적음", "보통", "많음"])
    def test_valid_outdoor_activities(self, outdoor_activity):
        data = {**VALID_LIFESTYLE, "outdoor_activity": outdoor_activity}
        schema = LifestyleSchema(**data)
        assert schema.outdoor_activity == outdoor_activity

    @pytest.mark.parametrize("hot_time_home_stay", ["아니요", "가끔", "자주", "거의 항상"])
    def test_valid_hot_time_home_stays(self, hot_time_home_stay):
        data = {**VALID_LIFESTYLE, "hot_time_home_stay": hot_time_home_stay}
        schema = LifestyleSchema(**data)
        assert schema.hot_time_home_stay == hot_time_home_stay

    def test_invalid_value_returns_422(self):
        data = {**VALID_LIFESTYLE, "main_activity_time": "저녁형"}
        with pytest.raises(ValidationError) as exc_info:
            LifestyleSchema(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("main_activity_time",) for e in errors)


class TestEnergyProfileSchema:
    """Req 2.4: EnergyProfile 필드 검증."""

    def test_valid_all_values(self):
        schema = EnergyProfileSchema(**VALID_ENERGY_PROFILE)
        assert schema.monthly_electricity_bill == 50000
        assert schema.monthly_goal_bill == 40000
        assert schema.has_fan is True

    def test_monthly_electricity_bill_min_boundary(self):
        """0원 허용."""
        data = {**VALID_ENERGY_PROFILE, "monthly_electricity_bill": 0}
        schema = EnergyProfileSchema(**data)
        assert schema.monthly_electricity_bill == 0

    def test_monthly_electricity_bill_max_boundary(self):
        """1,000,000원 허용."""
        data = {**VALID_ENERGY_PROFILE, "monthly_electricity_bill": 1000000}
        schema = EnergyProfileSchema(**data)
        assert schema.monthly_electricity_bill == 1000000

    def test_monthly_electricity_bill_below_min(self):
        """-1은 거부."""
        data = {**VALID_ENERGY_PROFILE, "monthly_electricity_bill": -1}
        with pytest.raises(ValidationError) as exc_info:
            EnergyProfileSchema(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("monthly_electricity_bill",) for e in errors)

    def test_monthly_electricity_bill_above_max(self):
        """1,000,001은 거부."""
        data = {**VALID_ENERGY_PROFILE, "monthly_electricity_bill": 1000001}
        with pytest.raises(ValidationError) as exc_info:
            EnergyProfileSchema(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("monthly_electricity_bill",) for e in errors)

    def test_monthly_goal_bill_optional_none(self):
        """monthly_goal_bill은 Optional (None 허용)."""
        data = {**VALID_ENERGY_PROFILE, "monthly_goal_bill": None}
        schema = EnergyProfileSchema(**data)
        assert schema.monthly_goal_bill is None

    def test_monthly_goal_bill_omitted(self):
        """monthly_goal_bill 생략 시 None."""
        data = {k: v for k, v in VALID_ENERGY_PROFILE.items() if k != "monthly_goal_bill"}
        schema = EnergyProfileSchema(**data)
        assert schema.monthly_goal_bill is None

    def test_monthly_goal_bill_zero_allowed(self):
        """monthly_goal_bill 0 허용 (ge=0)."""
        data = {**VALID_ENERGY_PROFILE, "monthly_goal_bill": 0}
        schema = EnergyProfileSchema(**data)
        assert schema.monthly_goal_bill == 0

    def test_monthly_goal_bill_negative_rejected(self):
        """monthly_goal_bill -1 거부."""
        data = {**VALID_ENERGY_PROFILE, "monthly_goal_bill": -1}
        with pytest.raises(ValidationError) as exc_info:
            EnergyProfileSchema(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("monthly_goal_bill",) for e in errors)

    @pytest.mark.parametrize("comfort_preference", ["시원한 편 선호", "보통", "절약 우선"])
    def test_valid_comfort_preferences(self, comfort_preference):
        data = {**VALID_ENERGY_PROFILE, "comfort_preference": comfort_preference}
        schema = EnergyProfileSchema(**data)
        assert schema.comfort_preference == comfort_preference

    @pytest.mark.parametrize("ac_type", ["없음", "벽걸이", "스탠드", "둘 다"])
    def test_valid_ac_types(self, ac_type):
        data = {**VALID_ENERGY_PROFILE, "ac_type": ac_type}
        schema = EnergyProfileSchema(**data)
        assert schema.ac_type == ac_type

    @pytest.mark.parametrize("curtain_type", ["없음", "일반", "암막"])
    def test_valid_curtain_types(self, curtain_type):
        data = {**VALID_ENERGY_PROFILE, "curtain_type": curtain_type}
        schema = EnergyProfileSchema(**data)
        assert schema.curtain_type == curtain_type

    def test_has_fan_boolean(self):
        for val in [True, False]:
            data = {**VALID_ENERGY_PROFILE, "has_fan": val}
            schema = EnergyProfileSchema(**data)
            assert schema.has_fan == val

    def test_invalid_comfort_preference(self):
        data = {**VALID_ENERGY_PROFILE, "comfort_preference": "매우 시원한 편"}
        with pytest.raises(ValidationError):
            EnergyProfileSchema(**data)


class TestFullProfileRequest:
    """Req 2.6: 3개 섹션 모두 필수."""

    def test_valid_full_profile(self):
        data = {
            "home_environment": VALID_HOME_ENVIRONMENT,
            "lifestyle": VALID_LIFESTYLE,
            "energy_profile": VALID_ENERGY_PROFILE,
        }
        profile = FullProfileRequest(**data)
        assert profile.home_environment.housing_type == "아파트"
        assert profile.lifestyle.main_activity_time == "아침형"
        assert profile.energy_profile.monthly_electricity_bill == 50000

    def test_missing_home_environment_returns_422(self):
        """Req 2.6: home_environment 누락 시 422."""
        data = {
            "lifestyle": VALID_LIFESTYLE,
            "energy_profile": VALID_ENERGY_PROFILE,
        }
        with pytest.raises(ValidationError) as exc_info:
            FullProfileRequest(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("home_environment",) for e in errors)

    def test_missing_lifestyle_returns_422(self):
        """Req 2.6: lifestyle 누락 시 422."""
        data = {
            "home_environment": VALID_HOME_ENVIRONMENT,
            "energy_profile": VALID_ENERGY_PROFILE,
        }
        with pytest.raises(ValidationError) as exc_info:
            FullProfileRequest(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("lifestyle",) for e in errors)

    def test_missing_energy_profile_returns_422(self):
        """Req 2.6: energy_profile 누락 시 422."""
        data = {
            "home_environment": VALID_HOME_ENVIRONMENT,
            "lifestyle": VALID_LIFESTYLE,
        }
        with pytest.raises(ValidationError) as exc_info:
            FullProfileRequest(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("energy_profile",) for e in errors)

    def test_nested_validation_error_propagates(self):
        """Req 2.5: 중첩 모델의 잘못된 값도 ValidationError."""
        data = {
            "home_environment": {**VALID_HOME_ENVIRONMENT, "housing_type": "INVALID"},
            "lifestyle": VALID_LIFESTYLE,
            "energy_profile": VALID_ENERGY_PROFILE,
        }
        with pytest.raises(ValidationError) as exc_info:
            FullProfileRequest(**data)
        errors = exc_info.value.errors()
        assert any("home_environment" in str(e["loc"]) for e in errors)


class TestFullProfileResponse:
    """FullProfileResponse 모델 존재 확인."""

    def test_response_model_exists(self):
        data = {
            "home_environment": VALID_HOME_ENVIRONMENT,
            "lifestyle": VALID_LIFESTYLE,
            "energy_profile": VALID_ENERGY_PROFILE,
        }
        response = FullProfileResponse(**data)
        assert response.home_environment.housing_type == "아파트"
        assert response.lifestyle.main_activity_time == "아침형"
        assert response.energy_profile.monthly_electricity_bill == 50000
