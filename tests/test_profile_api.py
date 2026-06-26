"""Tests for Profile API: PUT /api/v1/profile.

Validates:
- Req 2.1: PUT /api/v1/profile saves home_environment + lifestyle + energy_profile, returns 200
- Req 2.5: Invalid input → 422 with field name and allowed conditions
- Req 2.6: Missing section → 422 with missing section name
- Req 2.7: Same user re-saving → upsert (overwrite)
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db
from app.main import app
from app.schemas.profile import (
    EnergyProfileSchema,
    FullProfileRequest,
    HomeEnvironmentSchema,
    LifestyleSchema,
)


# ---------------------------------------------------------------------------
# Fake DB for isolation (same pattern as existing tests)
# ---------------------------------------------------------------------------


class FakeDb:
    def __init__(self) -> None:
        self.added: list = []
        self.commits = 0

    def add(self, value: Any) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value: Any) -> None:
        pass

    def query(self, model):
        return FakeQuery(self, model)

    def flush(self) -> None:
        pass

    def get_bind(self):
        raise AttributeError("No real DB")


class FakeQuery:
    """Minimal query mock for profile repository upsert lookups."""

    def __init__(self, db: FakeDb, model: Any) -> None:
        self._db = db
        self._model = model
        self._filters: list = []

    def filter(self, *args):
        self._filters.extend(args)
        return self

    def first(self):
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def valid_profile_payload() -> Dict[str, Any]:
    return {
        "home_environment": {
            "housing_type": "아파트",
            "direction": "남향",
            "floor_level": "중층",
            "building_age": "보통",
            "insulation_level": "보통",
            "window_size": "보통",
            "ventilation_level": "보통",
            "window_sealing": "보통",
        },
        "lifestyle": {
            "main_activity_time": "아침형",
            "daytime_home_stay": "종일 재택",
            "sleep_time": "밤",
            "outdoor_activity": "보통",
            "hot_time_home_stay": "가끔",
        },
        "energy_profile": {
            "monthly_electricity_bill": 50000,
            "monthly_goal_bill": 42000,
            "comfort_preference": "보통",
            "ac_type": "벽걸이",
            "has_fan": True,
            "curtain_type": "일반",
        },
    }


def make_client(fake_db: FakeDb) -> TestClient:
    """Create TestClient with fake DB override (bypasses real DB and auth)."""
    app.dependency_overrides[get_db] = lambda: fake_db
    return TestClient(app)


# ---------------------------------------------------------------------------
# Req 2.1: PUT /api/v1/profile saves and returns 200
# ---------------------------------------------------------------------------


class TestProfileUpsertSuccess:
    """Req 2.1: Valid profile data → 200 OK with stored profile."""

    def test_valid_full_profile_returns_200(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["home_environment"]["housing_type"] == "아파트"
        assert body["data"]["lifestyle"]["main_activity_time"] == "아침형"
        assert body["data"]["energy_profile"]["monthly_electricity_bill"] == 50000

    def test_minimal_energy_profile_without_optional_fields(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        """energy_profile에서 optional 필드를 제외해도 성공."""
        fake_db = FakeDb()
        client = make_client(fake_db)
        valid_profile_payload["energy_profile"] = {
            "monthly_electricity_bill": 30000,
            "comfort_preference": "절약 우선",
            "ac_type": "없음",
            "has_fan": False,
            "curtain_type": "없음",
        }

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["energy_profile"]["monthly_goal_bill"] is None
        assert data["energy_profile"]["monthly_electricity_bill"] == 30000


# ---------------------------------------------------------------------------
# Req 2.5: Invalid input → 422 with field name and allowed conditions
# ---------------------------------------------------------------------------


class TestProfileValidationErrors:
    """Req 2.5: Invalid enum/field values → 422."""

    def test_invalid_housing_type_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        valid_profile_payload["home_environment"]["housing_type"] = "무허가건물"

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422
        body = response.json()
        assert "detail" in body

    def test_invalid_direction_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        valid_profile_payload["home_environment"]["direction"] = "위쪽"

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422

    def test_invalid_main_activity_time_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        valid_profile_payload["lifestyle"]["main_activity_time"] = "항상"

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422

    def test_invalid_comfort_preference_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        valid_profile_payload["energy_profile"]["comfort_preference"] = "극한절약"

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422

    def test_monthly_bill_negative_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        valid_profile_payload["energy_profile"]["monthly_electricity_bill"] = -1

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422

    def test_monthly_bill_exceeds_max_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        valid_profile_payload["energy_profile"]["monthly_electricity_bill"] = 1_000_001

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422

    def test_has_fan_non_boolean_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        valid_profile_payload["energy_profile"]["has_fan"] = "maybe"

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Req 2.6: Missing section → 422 with missing section name
# ---------------------------------------------------------------------------


class TestProfileMissingSections:
    """Req 2.6: Missing required section → 422."""

    def test_missing_home_environment_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        del valid_profile_payload["home_environment"]

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422
        body = response.json()
        assert "detail" in body

    def test_missing_lifestyle_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        del valid_profile_payload["lifestyle"]

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422

    def test_missing_energy_profile_returns_422(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)
        del valid_profile_payload["energy_profile"]

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert response.status_code == 422

    def test_empty_body_returns_422(self, user_id: uuid.UUID) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json={},
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Req 2.7: Same user re-saving → upsert (overwrite)
# ---------------------------------------------------------------------------


class TestProfileUpsertIdempotence:
    """Req 2.7: Repeated saves overwrite rather than duplicate."""

    def test_second_save_returns_200_with_updated_data(
        self, user_id: uuid.UUID, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)

        # First save
        first_response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )
        assert first_response.status_code == 200

        # Update and re-save
        valid_profile_payload["home_environment"]["housing_type"] = "원룸"
        valid_profile_payload["energy_profile"]["monthly_electricity_bill"] = 70000

        second_response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": str(user_id)},
            json=valid_profile_payload,
        )

        assert second_response.status_code == 200
        data = second_response.json()["data"]
        assert data["home_environment"]["housing_type"] == "원룸"
        assert data["energy_profile"]["monthly_electricity_bill"] == 70000


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------


class TestProfileAuthentication:
    """Profile endpoint requires valid X-User-Id header."""

    def test_missing_user_id_header_returns_401(
        self, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)

        response = client.put(
            "/api/v1/profile",
            json=valid_profile_payload,
        )

        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "UNAUTHORIZED"

    def test_invalid_uuid_format_returns_401(
        self, valid_profile_payload: Dict[str, Any]
    ) -> None:
        fake_db = FakeDb()
        client = make_client(fake_db)

        response = client.put(
            "/api/v1/profile",
            headers={"X-User-Id": "not-a-uuid"},
            json=valid_profile_payload,
        )

        assert response.status_code == 401
        body = response.json()
        assert body["error"]["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# Schema validation unit tests
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """Direct schema validation tests for FullProfileRequest."""

    def test_valid_profile_schema_validates(self) -> None:
        data = {
            "home_environment": {
                "housing_type": "원룸",
                "direction": "북향",
                "floor_level": "반지하",
                "building_age": "신축",
                "insulation_level": "좋음",
                "window_size": "작음",
                "ventilation_level": "잘됨",
                "window_sealing": "잘 막힘",
            },
            "lifestyle": {
                "main_activity_time": "불규칙",
                "daytime_home_stay": "거의 없음",
                "sleep_time": "불규칙",
                "outdoor_activity": "많음",
                "hot_time_home_stay": "거의 항상",
            },
            "energy_profile": {
                "monthly_electricity_bill": 0,
                "comfort_preference": "시원한 편 선호",
                "ac_type": "둘 다",
                "has_fan": True,
                "curtain_type": "암막",
            },
        }
        profile = FullProfileRequest(**data)
        assert profile.home_environment.housing_type == "원룸"
        assert profile.lifestyle.hot_time_home_stay == "거의 항상"
        assert profile.energy_profile.monthly_electricity_bill == 0

    def test_boundary_bill_values(self) -> None:
        """monthly_electricity_bill at 0 and 1,000,000 should be valid."""
        schema_zero = EnergyProfileSchema(
            monthly_electricity_bill=0,
            comfort_preference="보통",
            ac_type="없음",
            has_fan=False,
            curtain_type="없음",
        )
        assert schema_zero.monthly_electricity_bill == 0

        schema_max = EnergyProfileSchema(
            monthly_electricity_bill=1_000_000,
            comfort_preference="보통",
            ac_type="없음",
            has_fan=False,
            curtain_type="없음",
        )
        assert schema_max.monthly_electricity_bill == 1_000_000

    def test_all_housing_types_valid(self) -> None:
        valid_types = ["원룸", "오피스텔", "아파트", "단독주택", "다세대"]
        for ht in valid_types:
            schema = HomeEnvironmentSchema(
                housing_type=ht,
                direction="남향",
                floor_level="중층",
                building_age="보통",
                insulation_level="보통",
                window_size="보통",
                ventilation_level="보통",
                window_sealing="보통",
            )
            assert schema.housing_type == ht

    def test_all_lifestyle_activity_times_valid(self) -> None:
        valid_times = ["아침형", "낮 활동", "야간 활동", "불규칙"]
        for at in valid_times:
            schema = LifestyleSchema(
                main_activity_time=at,
                daytime_home_stay="거의 없음",
                sleep_time="밤",
                outdoor_activity="적음",
                hot_time_home_stay="아니요",
            )
            assert schema.main_activity_time == at
