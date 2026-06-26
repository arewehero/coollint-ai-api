"""Tests for Task 15.1 (AI logging) and Task 16.1 (Request ID middleware + error handler).

Validates:
- Requirements 10.3: AIGenerationLog records request_type, prompt_version, model_name, latency_ms, success, error_code
- Requirements 10.4: AI_LOG_PAYLOAD=true saves request_payload + response_payload
- Requirements 10.5: AI_LOG_PAYLOAD=false stores payload as null
- Requirements 12.3: Consistent error format (success, error, meta)
- Requirements 12.4: Per-request UUID v4 request_id in X-Request-Id header and error response
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.errors import ApiException, ErrorCode, api_exception_handler, request_id_from_request
from app.dependencies import get_db
from app.main import app
from app.models.recommendation import AIGenerationLog
from app.schemas.common import ApiFailureResponse, ApiMeta
from app.services.ai_logging import build_ai_generation_log, hash_payload, record_ai_generation_log


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
    def __init__(self, db: FakeDb, model: Any) -> None:
        self._db = db
        self._model = model

    def filter(self, *args):
        return self

    def first(self):
        return None


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def make_client(fake_db: FakeDb | None = None) -> TestClient:
    """Create TestClient with fake DB override."""
    db = fake_db or FakeDb()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


# ============================================================================
# Task 15.1: AI Logging Tests
# ============================================================================


class TestBuildAIGenerationLog:
    """Tests for build_ai_generation_log - verifies AIGenerationLog is created with all required fields."""

    def test_all_required_fields_recorded(self):
        """Req 10.3: request_type, prompt_version, model_name, latency_ms, success, error_code are recorded."""
        log = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="lifestyle_analysis",
            prompt_version="v0.3-mock",
            model_name="anthropic.claude-3-haiku",
            success=True,
            latency_ms=245,
            error_code=None,
            request_payload={"scores": {"morning_score": 8}},
            response_payload={"primary_type": "아침형"},
        )

        assert isinstance(log, AIGenerationLog)
        assert log.request_type == "lifestyle_analysis"
        assert log.prompt_version == "v0.3-mock"
        assert log.model_name == "anthropic.claude-3-haiku"
        assert log.latency_ms == 245
        assert log.success is True
        assert log.error_code is None

    def test_error_case_fields_recorded(self):
        """Req 10.3: error_code is recorded on failure."""
        log = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="daily_plan_copy",
            prompt_version="v0.3-mock",
            model_name="mock-ai-client",
            success=False,
            latency_ms=8001,
            error_code="TIMEOUT",
            request_payload={"test": "data"},
            response_payload=None,
        )

        assert log.success is False
        assert log.error_code == "TIMEOUT"
        assert log.latency_ms == 8001

    def test_payload_included_when_log_payload_true(self):
        """Req 10.4: AI_LOG_PAYLOAD=true includes request_payload and response_payload."""
        request_data = {"scores": {"morning_score": 8}, "profile": {"lifestyle": {}}}
        response_data = {"primary_type": "아침형", "confidence": 0.87}

        log = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="lifestyle_analysis",
            prompt_version="v0.3",
            model_name="mock",
            success=True,
            latency_ms=100,
            request_payload=request_data,
            response_payload=response_data,
            log_payload=True,
        )

        assert log.request_payload is not None
        assert log.response_payload is not None
        assert log.request_payload["scores"]["morning_score"] == 8
        assert log.response_payload["primary_type"] == "아침형"

    def test_payload_null_when_log_payload_false(self):
        """Req 10.5: AI_LOG_PAYLOAD=false stores payload as null."""
        log = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="daily_plan_copy",
            prompt_version="v0.3",
            model_name="mock",
            success=True,
            latency_ms=50,
            request_payload={"input": "data"},
            response_payload={"output": "result"},
            log_payload=False,
        )

        assert log.request_payload is None
        assert log.response_payload is None

    def test_default_log_payload_uses_settings(self):
        """When log_payload is not specified, uses settings.ai_log_payload (default=False)."""
        log = build_ai_generation_log(
            user_id=None,
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
            request_payload={"hello": "world"},
            response_payload={"ok": True},
        )

        # Default is False per config
        assert log.request_payload is None
        assert log.response_payload is None

    def test_input_hash_generated_from_request_payload(self):
        """input_hash is generated using SHA-256 from request_payload for same-input tracking."""
        payload = {"scores": {"morning_score": 8}, "profile": {"lifestyle": {}}}

        log = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="lifestyle_analysis",
            prompt_version="v0.3",
            model_name="mock",
            success=True,
            request_payload=payload,
            response_payload=None,
            log_payload=False,
        )

        assert log.input_hash is not None
        # Verify it's a valid SHA-256 hex string (64 chars)
        assert len(log.input_hash) == 64
        assert all(c in "0123456789abcdef" for c in log.input_hash)

    def test_input_hash_is_none_when_no_request_payload(self):
        """input_hash is None when request_payload is None."""
        log = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
            request_payload=None,
            response_payload=None,
        )

        assert log.input_hash is None

    def test_same_payload_produces_same_input_hash(self):
        """Same request_payload always produces the same input_hash."""
        payload = {"key": "value", "nested": {"a": 1}}

        log1 = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
            request_payload=payload,
            response_payload=None,
        )
        log2 = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
            request_payload=payload,
            response_payload=None,
        )

        assert log1.input_hash == log2.input_hash

    def test_different_payload_produces_different_input_hash(self):
        """Different request_payloads produce different input_hashes."""
        log1 = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
            request_payload={"a": 1},
            response_payload=None,
        )
        log2 = build_ai_generation_log(
            user_id=uuid.uuid4(),
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
            request_payload={"a": 2},
            response_payload=None,
        )

        assert log1.input_hash != log2.input_hash

    def test_user_id_stored(self):
        """user_id is recorded in the log."""
        uid = uuid.uuid4()
        log = build_ai_generation_log(
            user_id=uid,
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
        )

        assert log.user_id == uid

    def test_user_id_optional(self):
        """user_id can be None (e.g., for system-level calls)."""
        log = build_ai_generation_log(
            user_id=None,
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
        )

        assert log.user_id is None


class TestHashPayload:
    """Tests for the hash_payload utility function."""

    def test_hash_is_sha256(self):
        """hash_payload uses SHA-256."""
        payload = {"hello": "world"}
        result = hash_payload(payload)

        # Verify it's a SHA-256 hex digest (64 characters)
        assert len(result) == 64

        # Verify against direct computation
        normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        expected = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        assert result == expected

    def test_hash_is_deterministic(self):
        """Same input always produces same hash."""
        payload = {"key": "value", "nested": {"x": [1, 2, 3]}}
        assert hash_payload(payload) == hash_payload(payload)

    def test_key_order_does_not_affect_hash(self):
        """Key order is normalized (sort_keys=True)."""
        payload1 = {"b": 2, "a": 1}
        payload2 = {"a": 1, "b": 2}
        assert hash_payload(payload1) == hash_payload(payload2)


# ============================================================================
# Task 16.1: Request ID Middleware and Error Handler Tests
# ============================================================================


class TestRequestIdMiddleware:
    """Tests for the request_id middleware - UUID v4 generation and X-Request-Id header."""

    def test_response_includes_x_request_id_header(self):
        """Req 12.4: Response includes X-Request-Id header."""
        client = make_client()
        response = client.get("/health")
        assert "X-Request-Id" in response.headers

    def test_request_id_is_uuid_v4_format(self):
        """Req 12.4: request_id is a valid UUID v4."""
        client = make_client()
        response = client.get("/health")
        request_id = response.headers["X-Request-Id"]

        # Validate UUID format
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4

    def test_each_request_gets_unique_request_id(self):
        """Each request gets a unique request_id."""
        client = make_client()
        response1 = client.get("/health")
        response2 = client.get("/health")

        assert response1.headers["X-Request-Id"] != response2.headers["X-Request-Id"]

    def test_client_provided_request_id_is_respected(self):
        """If client provides X-Request-Id header, it's used instead of generating a new one."""
        client = make_client()
        custom_id = str(uuid.uuid4())
        response = client.get("/health", headers={"X-Request-Id": custom_id})

        assert response.headers["X-Request-Id"] == custom_id


class TestErrorHandlerFormat:
    """Tests for error response format - consistent structure with meta.request_id."""

    def test_error_response_has_consistent_format(self):
        """Req 12.3: Error responses use format {success: false, error: {code, message}, meta: {request_id}}."""
        client = make_client()
        # Trigger a 401 by calling an auth-required endpoint without X-User-Id
        response = client.put("/api/v1/profile", json={"home_environment": {}})

        assert response.status_code == 401
        body = response.json()

        # Verify structure
        assert body["success"] is False
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert "meta" in body
        assert "request_id" in body["meta"]

    def test_error_meta_request_id_matches_header(self):
        """Req 12.4: meta.request_id in error body matches X-Request-Id response header."""
        client = make_client()
        response = client.put("/api/v1/profile", json={"home_environment": {}})

        body = response.json()
        header_request_id = response.headers["X-Request-Id"]

        assert body["meta"]["request_id"] == header_request_id

    def test_error_meta_request_id_is_uuid_v4(self):
        """Req 12.4: meta.request_id is a valid UUID v4."""
        client = make_client()
        response = client.put("/api/v1/profile", json={"data": "test"})
        body = response.json()

        request_id = body["meta"]["request_id"]
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4

    def test_invalid_uuid_header_returns_401_with_error_format(self):
        """Req 12.3: 401 from invalid UUID follows the consistent format."""
        client = make_client()
        response = client.put(
            "/api/v1/profile",
            json={"data": "test"},
            headers={"X-User-Id": "not-a-uuid"},
        )

        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "UNAUTHORIZED"
        assert "message" in body["error"]
        assert "meta" in body
        assert "request_id" in body["meta"]

    def test_error_format_with_custom_request_id(self):
        """Req 12.4: Custom X-Request-Id is reflected in error meta."""
        client = make_client()
        custom_id = str(uuid.uuid4())
        response = client.put(
            "/api/v1/profile",
            json={"data": "test"},
            headers={"X-Request-Id": custom_id},
        )

        assert response.status_code == 401
        body = response.json()
        assert body["meta"]["request_id"] == custom_id


class TestApiExceptionFromErrorCode:
    """Tests for ApiException.from_error_code helper."""

    def test_from_error_code_uses_defaults(self):
        exc = ApiException.from_error_code(ErrorCode.UNAUTHORIZED)
        assert exc.status_code == 401
        assert exc.code == "UNAUTHORIZED"
        assert exc.message == "인증에 실패했습니다."

    def test_from_error_code_custom_message(self):
        exc = ApiException.from_error_code(
            ErrorCode.NOT_FOUND,
            message="해당 행동을 찾을 수 없습니다.",
        )
        assert exc.status_code == 404
        assert exc.code == "NOT_FOUND"
        assert exc.message == "해당 행동을 찾을 수 없습니다."

    def test_from_error_code_with_details(self):
        exc = ApiException.from_error_code(
            ErrorCode.VALIDATION_ERROR,
            details={"field": "monthly_electricity_bill", "reason": "must be >= 0"},
        )
        assert exc.details["field"] == "monthly_electricity_bill"


class TestRecordAIGenerationLog:
    """Tests for record_ai_generation_log - verifies DB persistence."""

    def test_record_adds_log_to_session(self):
        """record_ai_generation_log adds the log to the DB session."""
        fake_db = FakeDb()
        log = record_ai_generation_log(
            fake_db,
            user_id=uuid.uuid4(),
            request_type="lifestyle_analysis",
            prompt_version="v0.3",
            model_name="mock-ai-client",
            success=True,
            latency_ms=150,
            request_payload={"test": "data"},
            response_payload={"result": "ok"},
        )

        assert len(fake_db.added) == 1
        assert fake_db.added[0] is log
        assert isinstance(log, AIGenerationLog)

    def test_record_commits_when_requested(self):
        """record_ai_generation_log commits when commit=True."""
        fake_db = FakeDb()
        record_ai_generation_log(
            fake_db,
            user_id=uuid.uuid4(),
            request_type="daily_plan_copy",
            prompt_version="v0.3",
            model_name="mock",
            success=True,
            commit=True,
        )

        assert fake_db.commits == 1

    def test_record_does_not_commit_by_default(self):
        """record_ai_generation_log does not commit by default."""
        fake_db = FakeDb()
        record_ai_generation_log(
            fake_db,
            user_id=uuid.uuid4(),
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
        )

        assert fake_db.commits == 0

    def test_record_respects_log_payload_setting(self):
        """record_ai_generation_log respects the log_payload parameter."""
        fake_db = FakeDb()
        log = record_ai_generation_log(
            fake_db,
            user_id=uuid.uuid4(),
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
            request_payload={"key": "value"},
            response_payload={"out": "data"},
            log_payload=True,
        )

        assert log.request_payload is not None
        assert log.response_payload is not None

    def test_record_hides_payload_when_disabled(self):
        """record_ai_generation_log hides payloads when log_payload=False."""
        fake_db = FakeDb()
        log = record_ai_generation_log(
            fake_db,
            user_id=uuid.uuid4(),
            request_type="test",
            prompt_version="v1",
            model_name="mock",
            success=True,
            request_payload={"key": "value"},
            response_payload={"out": "data"},
            log_payload=False,
        )

        assert log.request_payload is None
        assert log.response_payload is None
        # But input_hash is still generated for tracking
        assert log.input_hash is not None


class TestConfigSettings:
    """Tests for AI_LOG_PAYLOAD configuration."""

    def test_ai_log_payload_default_is_false(self):
        """AI_LOG_PAYLOAD defaults to False."""
        assert settings.ai_log_payload is False

    def test_ai_log_payload_is_boolean(self):
        """AI_LOG_PAYLOAD is a boolean setting."""
        assert isinstance(settings.ai_log_payload, bool)
