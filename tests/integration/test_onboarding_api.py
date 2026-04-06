"""API contract tests for onboarding endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from wxtools.interfaces.api.app import create_app
from wxtools.interfaces.api.models import OnboardingStatusData


@pytest.fixture()
def client_and_token():
    app, token = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    return client, token


def _headers(token: str) -> dict:
    return {"X-Session-Token": token}


def _assert_success_envelope(response_json: dict) -> dict:
    assert response_json["ok"] is True
    assert response_json["error"] is None
    return response_json["data"]


def _assert_error_envelope(response_json: dict, expected_code: str | None = None) -> dict:
    assert response_json["ok"] is False
    assert response_json["data"] is None
    assert response_json["error"] is not None
    if expected_code:
        assert response_json["error"]["code"] == expected_code
    return response_json["error"]


class TestOnboardingStatusContract:
    def test_status_returns_envelope(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/onboarding/status", headers=_headers(token))
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        # Validate against pydantic model
        OnboardingStatusData(**data)
        assert "current_step" in data
        assert "is_complete" in data
        assert "message" in data

    def test_status_requires_auth(self, client_and_token):
        client, _token = client_and_token
        r = client.get("/api/onboarding/status", headers={"X-Session-Token": "wrong"})
        assert r.status_code == 401


class TestOnboardingExtractKeyContract:
    def test_extract_key_requires_auth(self, client_and_token):
        client, _token = client_and_token
        r = client.post(
            "/api/onboarding/extract-key",
            json={"account": "wxid_test"},
            headers={"X-Session-Token": "wrong"},
        )
        assert r.status_code == 401

    def test_extract_key_returns_envelope_on_error(self, client_and_token):
        """On a test machine without WeChat, extraction should fail with a known error."""
        client, token = client_and_token
        r = client.post(
            "/api/onboarding/extract-key",
            json={"account": "wxid_test"},
            headers=_headers(token),
        )
        # Expect an error envelope (platform not supported or DB not found)
        assert r.status_code in (404, 500, 501)
        _assert_error_envelope(r.json())


class TestOnboardingVerifyContract:
    def test_verify_requires_auth(self, client_and_token):
        client, _token = client_and_token
        r = client.post(
            "/api/onboarding/verify",
            json={"account": "wxid_test"},
            headers={"X-Session-Token": "wrong"},
        )
        assert r.status_code == 401

    def test_verify_returns_envelope_on_missing_key(self, client_and_token):
        """Without a stored key, verify should fail with KEY_NOT_FOUND."""
        client, token = client_and_token
        r = client.post(
            "/api/onboarding/verify",
            json={"account": "wxid_nonexistent"},
            headers=_headers(token),
        )
        assert r.status_code == 404
        _assert_error_envelope(r.json(), "KEY_NOT_FOUND")
