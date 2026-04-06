"""API contract tests — verify every endpoint returns a valid ApiEnvelope."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from wxtools.interfaces.api.app import create_app
from wxtools.interfaces.api.models import (
    ApiEnvelope,
    ApiErrorDetail,
    CacheStatusData,
    ExportTemplatesData,
    HomeSummaryData,
    KeyStatusItem,
    WorkspaceData,
    WorkspaceDeleteData,
    WorkspaceSummary,
)


@pytest.fixture()
def client_and_token():
    app, token = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    return client, token


def _headers(token: str) -> dict:
    return {"X-Session-Token": token}


def _assert_success_envelope(response_json: dict) -> dict:
    """Assert response matches ApiEnvelope success shape, return data."""
    assert "ok" in response_json
    assert "data" in response_json
    assert "error" in response_json
    assert response_json["ok"] is True
    assert response_json["error"] is None
    return response_json["data"]


def _assert_error_envelope(response_json: dict, expected_code: str | None = None) -> dict:
    """Assert response matches ApiEnvelope error shape, return error."""
    assert response_json["ok"] is False
    assert response_json["data"] is None
    assert response_json["error"] is not None
    err = response_json["error"]
    assert "code" in err
    assert "message" in err
    if expected_code:
        assert err["code"] == expected_code
    # Validate against Pydantic model
    ApiErrorDetail(**err)
    return err


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealthContract:
    def test_health_returns_envelope(self, client_and_token):
        client, _token = client_and_token
        r = client.get("/api/health")
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        assert data["status"] == "ok"
        assert "version" in data


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class TestAccountsContract:
    def test_list_accounts_envelope(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/accounts", headers=_headers(token))
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

class TestHomeContract:
    def test_summary_envelope(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/home/summary", headers=_headers(token))
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        # Validate against Pydantic model
        HomeSummaryData(**data)


# ---------------------------------------------------------------------------
# Key
# ---------------------------------------------------------------------------

class TestKeyContract:
    def test_key_status_envelope(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/key/status", headers=_headers(token))
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        assert isinstance(data, list)
        for item in data:
            KeyStatusItem(**item)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class TestCacheContract:
    def test_cache_status_envelope(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/cache/status", headers=_headers(token))
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        CacheStatusData(**data)

    def test_cache_clear_empty_returns_error_envelope(self, client_and_token):
        client, token = client_and_token
        r = client.post(
            "/api/cache/clear",
            json={"account": None},
            headers=_headers(token),
        )
        # Cache is likely empty in test — expect 404 error envelope
        if r.status_code == 404:
            _assert_error_envelope(r.json(), "CACHE_EMPTY")
        else:
            # If it succeeds (unlikely in test), still should be an envelope
            _assert_success_envelope(r.json())


# ---------------------------------------------------------------------------
# Export templates
# ---------------------------------------------------------------------------

class TestExportContract:
    def test_templates_envelope(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/export/templates", headers=_headers(token))
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        ExportTemplatesData(**data)


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------

class TestWorkspacesContract:
    def test_list_workspaces_envelope(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/workspaces", headers=_headers(token))
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        assert isinstance(data, list)

    def test_create_and_get_envelope(self, client_and_token):
        client, token = client_and_token
        h = _headers(token)

        # Create
        r = client.post("/api/workspaces", json={"name": "Contract WS"}, headers=h)
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        WorkspaceData(**data)
        ws_id = data["id"]

        # Get
        r = client.get(f"/api/workspaces/{ws_id}", headers=h)
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        WorkspaceData(**data)

        # Delete
        r = client.delete(f"/api/workspaces/{ws_id}", headers=h)
        assert r.status_code == 200
        data = _assert_success_envelope(r.json())
        WorkspaceDeleteData(**data)

    def test_get_nonexistent_returns_error_envelope(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/workspaces/does-not-exist", headers=_headers(token))
        assert r.status_code == 404
        _assert_error_envelope(r.json(), "WORKSPACE_NOT_FOUND")
