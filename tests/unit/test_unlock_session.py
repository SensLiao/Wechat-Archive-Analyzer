"""Tests for session token lifecycle."""
import pytest
from wxtools.core.unlock_session import UnlockSession

@pytest.fixture
def session_mgr(tmp_path):
    return UnlockSession(tmp_path / "session")

def test_no_session_initially(session_mgr):
    assert session_mgr.get_key("wechat", "wxid_test") is None

def test_create_and_retrieve(session_mgr):
    key = b"secret_key_32_bytes_long_padding!"
    session_mgr.create("wechat", "wxid_test", key, ttl_minutes=60)
    retrieved = session_mgr.get_key("wechat", "wxid_test")
    assert retrieved == key

def test_expired_session_returns_none(session_mgr):
    key = b"secret_key_32_bytes_long_padding!"
    session_mgr.create("wechat", "wxid_test", key, ttl_minutes=0)
    assert session_mgr.get_key("wechat", "wxid_test") is None

def test_clear_session(session_mgr):
    key = b"secret_key_32_bytes_long_padding!"
    session_mgr.create("wechat", "wxid_test", key, ttl_minutes=60)
    session_mgr.clear("wechat", "wxid_test")
    assert session_mgr.get_key("wechat", "wxid_test") is None

def test_clear_all(session_mgr):
    key = b"key_one_32_bytes_long_padding!!!"
    session_mgr.create("wechat", "wxid_a", key, ttl_minutes=60)
    session_mgr.create("wechat", "wxid_b", key, ttl_minutes=60)
    session_mgr.clear_all()
    assert session_mgr.get_key("wechat", "wxid_a") is None
    assert session_mgr.get_key("wechat", "wxid_b") is None
