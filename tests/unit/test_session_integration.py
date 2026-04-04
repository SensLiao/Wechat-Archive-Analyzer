"""Tests verifying session-aware key retrieval logic."""
import pytest
from wxtools.core.keystore import Keystore
from wxtools.core.unlock_session import UnlockSession

def test_session_key_retrieval_bypasses_password(tmp_path):
    keys_dir = tmp_path / "keys"
    session_dir = tmp_path / "session"
    ks = Keystore(keys_dir)
    raw_key = b"test_key_32_bytes_long_padding!!"
    ks.store_key("wechat", "wxid_test", raw_key, protection="password", password="mypass")
    session = UnlockSession(session_dir)
    session.create("wechat", "wxid_test", raw_key, ttl_minutes=60)
    assert session.get_key("wechat", "wxid_test") == raw_key
    with pytest.raises(Exception):
        ks.get_key("wechat", "wxid_test")

def test_expired_session_forces_password(tmp_path):
    session_dir = tmp_path / "session"
    session = UnlockSession(session_dir)
    raw_key = b"test_key_32_bytes_long_padding!!"
    session.create("wechat", "wxid_test", raw_key, ttl_minutes=0)
    assert session.get_key("wechat", "wxid_test") is None
