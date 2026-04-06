"""Tests for session token lifecycle with SecretBackend."""
import json
import sys

import pytest

from wxtools.infrastructure.secrets.unlock_session import UnlockSession


@pytest.fixture
def session_mgr(tmp_path):
    return UnlockSession(tmp_path / "session")


class TestUnlockSessionLifecycle:
    def test_no_session_initially(self, session_mgr):
        assert session_mgr.get_key("wechat", "wxid_test") is None

    def test_create_and_retrieve_with_password(self, session_mgr):
        key = b"secret_key_32_bytes_long_padding!"
        session_mgr.create("wechat", "wxid_test", key,
                           ttl_minutes=60, backend_name="password-file",
                           password="sesspass")
        retrieved = session_mgr.get_key("wechat", "wxid_test", password="sesspass")
        assert retrieved == key

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI only on Windows")
    def test_create_and_retrieve_with_dpapi(self, session_mgr):
        key = b"secret_key_32_bytes_long_padding!"
        session_mgr.create("wechat", "wxid_test", key,
                           ttl_minutes=60, backend_name="windows-dpapi")
        retrieved = session_mgr.get_key("wechat", "wxid_test")
        assert retrieved == key

    def test_expired_session_returns_none(self, session_mgr):
        key = b"secret_key_32_bytes_long_padding!"
        session_mgr.create("wechat", "wxid_test", key,
                           ttl_minutes=0, backend_name="password-file",
                           password="p")
        assert session_mgr.get_key("wechat", "wxid_test", password="p") is None

    def test_clear_session(self, session_mgr):
        key = b"secret_key_32_bytes_long_padding!"
        session_mgr.create("wechat", "wxid_test", key,
                           ttl_minutes=60, backend_name="password-file",
                           password="p")
        session_mgr.clear("wechat", "wxid_test")
        assert session_mgr.get_key("wechat", "wxid_test", password="p") is None

    def test_clear_all(self, session_mgr):
        key = b"key_one_32_bytes_long_padding!!!"
        session_mgr.create("wechat", "wxid_a", key,
                           ttl_minutes=60, backend_name="password-file",
                           password="p")
        session_mgr.create("wechat", "wxid_b", key,
                           ttl_minutes=60, backend_name="password-file",
                           password="p")
        session_mgr.clear_all()
        assert session_mgr.get_key("wechat", "wxid_a", password="p") is None
        assert session_mgr.get_key("wechat", "wxid_b", password="p") is None

    def test_session_file_has_backend_name(self, session_mgr):
        key = b"secret_key_32_bytes_long_padding!"
        session_mgr.create("wechat", "wxid_meta", key,
                           ttl_minutes=60, backend_name="password-file",
                           password="p")
        path = session_mgr._session_path("wechat", "wxid_meta")
        data = json.loads(path.read_text("utf-8"))
        assert data["protection"] == "password-file"
