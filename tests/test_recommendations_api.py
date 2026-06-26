from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, Optional, Tuple

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.dependencies import get_db, get_profile_repository, get_recommendation_repository
from app.main import app


class FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def add(self, value: Any) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value: Any) -> None:
        return None

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeProfileRepository:
    def __init__(
        self,
        profile: Optional[Dict[str, Any]] = None,
        profiles: Optional[Dict[uuid.UUID, Dict[str, Any]]] = None,
        active_user_ids: Optional[list[uuid.UUID]] = None,
    ) -> None:
        self.profile = profile
        self.profiles = profiles or {}
        self.active_user_ids = active_user_ids

    def get_profile(self, db: FakeDb, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        if self.profiles:
            return self.profiles.get(user_id)
        return self.profile

    def list_active_user_ids_with_profiles(self, db: FakeDb) -> list[uuid.UUID]:
        if self.active_user_ids is not None:
            return self.active_user_ids
        return list(self.profiles)


class FakeRecommendationRepository:
    def __init__(self) -> None:
        self.plans: Dict[Tuple[uuid.UUID, dt.date], Any] = {}
        self.logs = []

    def get_daily_plan(self, db: FakeDb, user_id: uuid.UUID, target_date: dt.date):
        return self.plans.get((user_id, target_date))

    def has_completed_actions(self, plan: Any) -> bool:
        return any(action.is_completed for action in plan.actions)

    def delete_plan(self, db: FakeDb, plan: Any) -> None:
        self.plans.pop((plan.user_id, plan.date), None)

    def create_daily_plan(self, db: FakeDb, *, lifestyle_analysis: Any, plan: Any, actions: Any):
        lifestyle_analysis.id = uuid.uuid4()
        plan.id = uuid.uuid4()
        plan.lifestyle_analysis = lifestyle_analysis
        plan.lifestyle_analysis_id = lifestyle_analysis.id
        plan.actions = list(actions)
        for action in plan.actions:
            action.id = uuid.uuid4()
            action.plan = plan
            action.plan_id = plan.id
        self.plans[(plan.user_id, plan.date)] = plan
        return plan

    def get_action_for_user(self, db: FakeDb, action_id: uuid.UUID, user_id: uuid.UUID):
        for plan_user_id, plan_date in self.plans:
            if plan_user_id != user_id:
                continue
            plan = self.plans[(plan_user_id, plan_date)]
            for action in plan.actions:
                if action.id == action_id:
                    return action
        return None

    def add_completion_log(self, db: FakeDb, log: Any) -> None:
        log.id = uuid.uuid4()
        self.logs.append(log)
        db.add(log)

    def list_actions_for_period(self, db: FakeDb, *, user_id: uuid.UUID, period_start: dt.date, period_end: dt.date):
        actions = []
        for (plan_user_id, plan_date), plan in self.plans.items():
            if plan_user_id == user_id and period_start <= plan_date <= period_end:
                actions.extend(plan.actions)
        return sorted(actions, key=lambda action: (action.date, action.sort_order))

    def list_daily_plans_for_period(self, db: FakeDb, *, user_id: uuid.UUID, period_start: dt.date, period_end: dt.date):
        return [
            plan
            for (plan_user_id, plan_date), plan in sorted(self.plans.items(), key=lambda item: item[0][1])
            if plan_user_id == user_id and period_start <= plan_date <= period_end
        ]


@pytest.fixture()
def fake_db() -> FakeDb:
    return FakeDb()


@pytest.fixture()
def fake_recommendation_repository() -> FakeRecommendationRepository:
    return FakeRecommendationRepository()


@pytest.fixture()
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def sample_profile() -> Dict[str, Any]:
    return {
        "energy_profile": {
            "monthly_electricity_bill": 50000,
            "monthly_goal_bill": 42000,
            "comfort_preference": "절약 우선",
            "ac_type": "벽걸이",
            "has_fan": True,
            "curtain_type": "암막",
        },
        "home_environment": {
            "housing_type": "원룸",
            "direction": "서향",
            "floor_level": "최상층",
            "building_age": "보통",
            "insulation_level": "보통",
            "window_size": "큼",
            "ventilation_level": "보통",
            "window_sealing": "보통",
        },
        "lifestyle": {
            "main_activity_time": "야간 활동",
            "daytime_home_stay": "거의 없음",
            "sleep_time": "새벽",
            "outdoor_activity": "보통",
            "hot_time_home_stay": "가끔",
        },
    }


@pytest.fixture(autouse=True)
def clear_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def make_client(
    fake_db: FakeDb,
    profile: Optional[Dict[str, Any]],
    recommendation_repository: FakeRecommendationRepository,
    profile_repository: Optional[FakeProfileRepository] = None,
) -> TestClient:
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_profile_repository] = lambda: profile_repository or FakeProfileRepository(profile)
    app.dependency_overrides[get_recommendation_repository] = lambda: recommendation_repository
    return TestClient(app)


def test_create_daily_plan_returns_profile_not_found(fake_db: FakeDb, fake_recommendation_repository: FakeRecommendationRepository, user_id: uuid.UUID) -> None:
    client = make_client(fake_db, None, fake_recommendation_repository)

    response = client.post(
        "/api/v1/recommendations/daily",
        headers={"X-User-Id": str(user_id)},
        json={"date": "2026-06-26", "force_regenerate": False},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PROFILE_NOT_FOUND"


def test_create_daily_plan_first_request_returns_201(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)

    response = client.post(
        "/api/v1/recommendations/daily",
        headers={"X-User-Id": str(user_id)},
        json={
            "date": "2026-06-26",
            "location": {"region_name": "서울"},
            "force_regenerate": False,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["date"] == "2026-06-26"
    assert body["data"]["status"] == "generated"
    assert body["data"]["daily_summary"]["total_estimated_saving_krw"] == 930
    assert len(body["data"]["actions"]) == 8
    assert "estimated_saving_krw" in body["data"]["actions"][0]


def test_daily_plan_actions_are_sorted_by_priority(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)

    response = client.post(
        "/api/v1/recommendations/daily",
        headers={"X-User-Id": str(user_id)},
        json={"date": "2026-06-26", "force_regenerate": False},
    )

    actions = response.json()["data"]["actions"]
    assert response.status_code == 201
    assert actions[0]["sort_order"] == 1
    assert actions[0]["action_type"] == "ac_temp_up"
    assert actions[1]["action_type"] == "timer_sleep"
    assert [action["sort_order"] for action in actions] == list(range(1, len(actions) + 1))


def test_lifestyle_analysis_ai_endpoint_uses_mock_client(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)

    response = client.post(
        "/api/v1/ai/lifestyle-analysis",
        headers={"X-User-Id": str(user_id)},
        json={
            "date": "2026-06-26",
            "scores": {"night_score": 82, "saving_priority_score": 70},
        },
    )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["analysis_id"]
    assert data["primary_type"] == "야간 활동형"
    assert data["secondary_type"] == "절약 우선형"
    assert 0 <= data["confidence"] <= 1


def test_create_daily_plan_same_date_returns_existing_plan(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    payload = {"date": "2026-06-26", "force_regenerate": False}

    first = client.post("/api/v1/recommendations/daily", headers={"X-User-Id": str(user_id)}, json=payload)
    second = client.post("/api/v1/recommendations/daily", headers={"X-User-Id": str(user_id)}, json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["data"]["plan_id"] == first.json()["data"]["plan_id"]


def test_create_daily_plan_force_regenerate_false_is_idempotent(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    payload = {"date": "2026-06-26", "force_regenerate": False}

    first = client.post("/api/v1/recommendations/daily", headers={"X-User-Id": str(user_id)}, json=payload)
    second = client.post("/api/v1/recommendations/daily", headers={"X-User-Id": str(user_id)}, json=payload)

    first_data = first.json()["data"]
    second_data = second.json()["data"]
    assert first_data["plan_id"] == second_data["plan_id"]
    assert first_data["daily_summary"] == second_data["daily_summary"]
    assert [action["action_id"] for action in first_data["actions"]] == [action["action_id"] for action in second_data["actions"]]


def test_get_daily_plan_without_saved_plan_returns_not_found(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)

    response = client.get(
        "/api/v1/recommendations/daily",
        headers={"X-User-Id": str(user_id)},
        params={"date": "2026-06-26"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RECOMMENDATION_NOT_FOUND"


def create_plan_and_get_first_action(
    client: TestClient,
    user_id: uuid.UUID,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    return create_plan_and_get_first_action_for_date(client, user_id, "2026-06-26")


def create_plan_and_get_first_action_for_date(
    client: TestClient,
    user_id: uuid.UUID,
    target_date: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    response = client.post(
        "/api/v1/recommendations/daily",
        headers={"X-User-Id": str(user_id)},
        json={"date": target_date, "force_regenerate": False},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    return data, data["actions"][0]


def test_toggle_action_complete_success(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    _, action = create_plan_and_get_first_action(client, user_id)

    response = client.patch(
        f"/api/v1/recommendations/actions/{action['action_id']}",
        headers={"X-User-Id": str(user_id)},
        json={"is_completed": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["action_id"] == action["action_id"]
    assert body["data"]["is_completed"] is True
    assert body["data"]["completed_at"] is not None
    assert body["data"]["delta"]["saving_krw"] == action["estimated_saving_krw"]
    assert fake_recommendation_repository.logs[-1].event_type == "completed"


def test_toggle_action_uncomplete_success(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    _, action = create_plan_and_get_first_action(client, user_id)
    client.patch(
        f"/api/v1/recommendations/actions/{action['action_id']}",
        headers={"X-User-Id": str(user_id)},
        json={"is_completed": True},
    )

    response = client.patch(
        f"/api/v1/recommendations/actions/{action['action_id']}",
        headers={"X-User-Id": str(user_id)},
        json={"is_completed": False},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["is_completed"] is False
    assert body["completed_at"] is None
    assert body["delta"]["saving_krw"] == -action["estimated_saving_krw"]
    assert fake_recommendation_repository.logs[-1].event_type == "uncompleted"
    assert fake_recommendation_repository.logs[-1].saving_krw_delta == -action["estimated_saving_krw"]


def test_toggle_action_duplicate_complete_returns_current_state_without_new_log(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    _, action = create_plan_and_get_first_action(client, user_id)
    first = client.patch(
        f"/api/v1/recommendations/actions/{action['action_id']}",
        headers={"X-User-Id": str(user_id)},
        json={"is_completed": True},
    )
    log_count = len(fake_recommendation_repository.logs)

    second = client.patch(
        f"/api/v1/recommendations/actions/{action['action_id']}",
        headers={"X-User-Id": str(user_id)},
        json={"is_completed": True},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    data = second.json()["data"]
    assert data["is_completed"] is True
    assert data["delta"] == {"saving_krw": 0, "energy_saving_kwh": 0.0, "co2_reduction_kg": 0.0}
    assert len(fake_recommendation_repository.logs) == log_count


def test_toggle_action_other_user_cannot_access(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    _, action = create_plan_and_get_first_action(client, user_id)
    other_user_id = uuid.uuid4()

    response = client.patch(
        f"/api/v1/recommendations/actions/{action['action_id']}",
        headers={"X-User-Id": str(other_user_id)},
        json={"is_completed": True},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RECOMMENDATION_NOT_FOUND"


def test_toggle_action_today_progress_calculation(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    plan, first_action = create_plan_and_get_first_action(client, user_id)
    second_action = plan["actions"][1]

    client.patch(
        f"/api/v1/recommendations/actions/{first_action['action_id']}",
        headers={"X-User-Id": str(user_id)},
        json={"is_completed": True},
    )
    response = client.patch(
        f"/api/v1/recommendations/actions/{second_action['action_id']}",
        headers={"X-User-Id": str(user_id)},
        json={"is_completed": True},
    )

    progress = response.json()["data"]["today_progress"]
    expected_completed_saving = first_action["estimated_saving_krw"] + second_action["estimated_saving_krw"]
    expected_total_saving = plan["daily_summary"]["total_estimated_saving_krw"]
    assert progress["completed_action_count"] == 2
    assert progress["total_action_count"] == len(plan["actions"])
    assert progress["completed_saving_krw"] == expected_completed_saving
    assert progress["today_estimated_saving_krw"] == expected_total_saving
    assert progress["goal_achievement_rate"] == round(expected_completed_saving / expected_total_saving * 100, 1)
    assert "오늘 목표" in progress["message"]


def complete_action(client: TestClient, user_id: uuid.UUID, action: Dict[str, Any]) -> None:
    response = client.patch(
        f"/api/v1/recommendations/actions/{action['action_id']}",
        headers={"X-User-Id": str(user_id)},
        json={"is_completed": True},
    )
    assert response.status_code == 200


def test_today_savings_summary_aggregation(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    plan, first_action = create_plan_and_get_first_action(client, user_id)
    complete_action(client, user_id, first_action)

    response = client.get(
        "/api/v1/savings/summary",
        headers={"X-User-Id": str(user_id)},
        params={"period": "today", "date": "2026-06-26"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["period"] == "today"
    assert data["period_start"] == "2026-06-26"
    assert data["period_end"] == "2026-06-26"
    assert data["completed_action_count"] == 1
    assert data["total_action_count"] == len(plan["actions"])
    assert data["total_saving_krw"] == first_action["estimated_saving_krw"]
    assert data["total_possible_saving_krw"] == plan["daily_summary"]["total_estimated_saving_krw"]
    assert data["monthly_projected_saving_krw"] == first_action["estimated_saving_krw"] * 30


def test_week_savings_summary_aggregation(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    _, monday_action = create_plan_and_get_first_action_for_date(client, user_id, "2026-06-22")
    _, friday_action = create_plan_and_get_first_action_for_date(client, user_id, "2026-06-26")
    complete_action(client, user_id, monday_action)
    complete_action(client, user_id, friday_action)

    response = client.get(
        "/api/v1/savings/summary",
        headers={"X-User-Id": str(user_id)},
        params={"period": "week", "date": "2026-06-26"},
    )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["period_start"] == "2026-06-22"
    assert data["period_end"] == "2026-06-28"
    assert data["completed_action_count"] == 2
    assert data["total_action_count"] == 16
    assert data["total_saving_krw"] == monday_action["estimated_saving_krw"] + friday_action["estimated_saving_krw"]


def test_month_savings_summary_aggregation(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    _, first_day_action = create_plan_and_get_first_action_for_date(client, user_id, "2026-06-01")
    _, target_day_action = create_plan_and_get_first_action_for_date(client, user_id, "2026-06-26")
    complete_action(client, user_id, first_day_action)
    complete_action(client, user_id, target_day_action)

    response = client.get(
        "/api/v1/savings/summary",
        headers={"X-User-Id": str(user_id)},
        params={"period": "month", "date": "2026-06-26"},
    )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["period_start"] == "2026-06-01"
    assert data["period_end"] == "2026-06-30"
    assert data["completed_action_count"] == 2
    assert data["total_action_count"] == 16
    assert data["total_saving_krw"] == first_day_action["estimated_saving_krw"] + target_day_action["estimated_saving_krw"]


def test_monthly_calendar_response(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    plan, first_action = create_plan_and_get_first_action(client, user_id)
    second_action = plan["actions"][1]
    complete_action(client, user_id, first_action)
    complete_action(client, user_id, second_action)

    response = client.get(
        "/api/v1/savings/calendar",
        headers={"X-User-Id": str(user_id)},
        params={"month": "2026-06"},
    )

    data = response.json()["data"]
    day_26 = next(day for day in data["days"] if day["date"] == "2026-06-26")
    expected_saving = first_action["estimated_saving_krw"] + second_action["estimated_saving_krw"]
    assert response.status_code == 200
    assert data["month"] == "2026-06"
    assert len(data["days"]) == 30
    assert day_26["completed_action_count"] == 2
    assert day_26["total_saving_krw"] == expected_saving
    assert data["monthly_total"]["saving_krw"] == expected_saving


def test_savings_summary_goal_on_track(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    plan, _ = create_plan_and_get_first_action(client, user_id)
    for action in plan["actions"]:
        complete_action(client, user_id, action)

    response = client.get(
        "/api/v1/savings/summary",
        headers={"X-User-Id": str(user_id)},
        params={"period": "today", "date": "2026-06-26"},
    )

    goal = response.json()["data"]["goal"]
    assert response.status_code == 200
    assert goal["monthly_electricity_bill"] == 50000
    assert goal["monthly_goal_bill"] == 42000
    assert goal["required_monthly_saving_krw"] == 8000
    assert goal["current_projected_saving_krw"] == 27900
    assert goal["on_track"] is True


def test_internal_job_without_token_fails(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    old_token = settings.internal_job_token
    settings.internal_job_token = "secret"
    try:
        profile_repository = FakeProfileRepository(profiles={user_id: sample_profile})
        client = make_client(fake_db, sample_profile, fake_recommendation_repository, profile_repository=profile_repository)

        response = client.post(
            "/api/v1/internal/jobs/generate-daily-recommendations",
            json={"date": "2026-06-26", "target": "all_active_users", "dry_run": True},
        )
    finally:
        settings.internal_job_token = old_token

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_internal_job_dry_run_success(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    second_user_id = uuid.uuid4()
    old_token = settings.internal_job_token
    settings.internal_job_token = "secret"
    try:
        profile_repository = FakeProfileRepository(
            profiles={user_id: sample_profile, second_user_id: sample_profile},
        )
        client = make_client(fake_db, sample_profile, fake_recommendation_repository, profile_repository=profile_repository)

        response = client.post(
            "/api/v1/internal/jobs/generate-daily-recommendations",
            headers={"X-Internal-Job-Token": "secret"},
            json={"date": "2026-06-26", "target": "all_active_users", "dry_run": True},
        )
    finally:
        settings.internal_job_token = old_token

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["total_users"] == 2
    assert data["generated_count"] == 2
    assert data["skipped_count"] == 0
    assert data["failed_count"] == 0
    assert fake_recommendation_repository.plans == {}


def test_internal_job_skips_existing_plan(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    old_token = settings.internal_job_token
    settings.internal_job_token = "secret"
    try:
        profile_repository = FakeProfileRepository(profiles={user_id: sample_profile})
        client = make_client(fake_db, sample_profile, fake_recommendation_repository, profile_repository=profile_repository)
        create_plan_and_get_first_action(client, user_id)

        response = client.post(
            "/api/v1/internal/jobs/generate-daily-recommendations",
            headers={"X-Internal-Job-Token": "secret"},
            json={"date": "2026-06-26", "target": "all_active_users", "dry_run": False},
        )
    finally:
        settings.internal_job_token = old_token

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["total_users"] == 1
    assert data["generated_count"] == 0
    assert data["skipped_count"] == 1
    assert data["failed_count"] == 0


def test_integrated_create_toggle_summary_flow(
    fake_db: FakeDb,
    fake_recommendation_repository: FakeRecommendationRepository,
    sample_profile: Dict[str, Any],
    user_id: uuid.UUID,
) -> None:
    client = make_client(fake_db, sample_profile, fake_recommendation_repository)
    plan, first_action = create_plan_and_get_first_action(client, user_id)
    complete_action(client, user_id, first_action)

    response = client.get(
        "/api/v1/savings/summary",
        headers={"X-User-Id": str(user_id)},
        params={"period": "today", "date": "2026-06-26"},
    )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["completed_action_count"] == 1
    assert data["total_action_count"] == len(plan["actions"])
    assert data["total_saving_krw"] == first_action["estimated_saving_krw"]
    assert data["total_possible_saving_krw"] == plan["daily_summary"]["total_estimated_saving_krw"]
