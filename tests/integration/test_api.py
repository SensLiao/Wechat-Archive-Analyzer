"""Integration tests for the local Web API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from wxtools.interfaces.api.app import create_app


@pytest.fixture()
def client_and_token():
    """Create a test client with the session token."""
    app, token = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    return client, token


@pytest.fixture()
def client(client_and_token):
    return client_and_token[0]


@pytest.fixture()
def headers(client_and_token):
    _, token = client_and_token
    return {"X-Session-Token": token}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_no_auth(self, client):
        """Health endpoint requires no auth."""
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["data"]["status"] == "ok"
        assert "version" in data["data"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_missing_token_returns_422_or_401(self, client):
        """Requests without token should fail."""
        r = client.get("/api/accounts")
        assert r.status_code in (401, 422)

    def test_wrong_token_returns_401(self, client):
        """Requests with wrong token should fail."""
        r = client.get("/api/accounts", headers={"X-Session-Token": "wrong"})
        assert r.status_code == 401

    def test_correct_token(self, client_and_token):
        """Requests with correct token should succeed."""
        client, token = client_and_token
        r = client.get("/api/accounts", headers={"X-Session-Token": token})
        # May return empty list but should not 401
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class TestAccounts:
    def test_list_accounts(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/accounts", headers={"X-Session-Token": token})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert isinstance(data["data"], list)


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

class TestHome:
    def test_summary(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/home/summary", headers={"X-Session-Token": token})
        assert r.status_code == 200
        envelope = r.json()
        assert envelope["ok"] is True
        data = envelope["data"]
        assert "accounts" in data
        assert "keys" in data
        assert "cache" in data


# ---------------------------------------------------------------------------
# Key
# ---------------------------------------------------------------------------

class TestKey:
    def test_key_status(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/key/status", headers={"X-Session-Token": token})
        assert r.status_code == 200
        envelope = r.json()
        assert envelope["ok"] is True
        assert isinstance(envelope["data"], list)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class TestCache:
    def test_cache_status(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/cache/status", headers={"X-Session-Token": token})
        assert r.status_code == 200
        envelope = r.json()
        assert envelope["ok"] is True
        assert "cache_dir" in envelope["data"]


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------

class TestWorkspaces:
    def test_list_empty(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/workspaces", headers={"X-Session-Token": token})
        assert r.status_code == 200
        envelope = r.json()
        assert envelope["ok"] is True
        assert isinstance(envelope["data"], list)

    def test_crud_workspace(self, client_and_token):
        client, token = client_and_token
        h = {"X-Session-Token": token}

        # Create
        r = client.post("/api/workspaces", json={"name": "Test WS"}, headers=h)
        assert r.status_code == 200
        envelope = r.json()
        assert envelope["ok"] is True
        ws = envelope["data"]
        assert ws["name"] == "Test WS"
        ws_id = ws["id"]

        # Get
        r = client.get(f"/api/workspaces/{ws_id}", headers=h)
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "Test WS"

        # Add items
        r = client.post(f"/api/workspaces/{ws_id}/items", json={
            "items": [{"type": "note", "title": "test note"}]
        }, headers=h)
        assert r.status_code == 200
        assert len(r.json()["data"]["items"]) == 1

        # Delete workspace
        r = client.delete(f"/api/workspaces/{ws_id}", headers=h)
        assert r.status_code == 200
        assert r.json()["data"]["deleted"] is True

    def test_get_nonexistent_workspace(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/workspaces/nonexistent", headers={"X-Session-Token": token})
        assert r.status_code == 404
        envelope = r.json()
        assert envelope["ok"] is False
        assert envelope["error"]["code"] == "WORKSPACE_NOT_FOUND"


# ---------------------------------------------------------------------------
# Export templates
# ---------------------------------------------------------------------------

class TestExportTemplates:
    def test_list_templates(self, client_and_token):
        client, token = client_and_token
        r = client.get("/api/export/templates", headers={"X-Session-Token": token})
        assert r.status_code == 200
        envelope = r.json()
        assert envelope["ok"] is True
        templates = envelope["data"]["templates"]
        assert isinstance(templates, list)
        assert len(templates) >= 3  # json, csv, html at minimum
