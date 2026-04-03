import sys
import pytest
from wxtools.core.keystore import Keystore


@pytest.fixture
def keystore(tmp_home):
    return Keystore(keys_dir=tmp_home / "keys")


def test_store_and_retrieve_password_mode(keystore):
    key = bytes.fromhex("ab" * 32)
    keystore.store_key("wechat", "wxid_test", key, protection="password", password="mypass")
    retrieved = keystore.get_key("wechat", "wxid_test", password="mypass")
    assert retrieved == key


def test_wrong_password_raises(keystore):
    key = bytes.fromhex("ab" * 32)
    keystore.store_key("wechat", "wxid_test", key, protection="password", password="correct")
    with pytest.raises(Exception):
        keystore.get_key("wechat", "wxid_test", password="wrong")


def test_list_keys_empty(keystore):
    assert keystore.list_keys() == []


def test_list_keys_after_store(keystore):
    key = bytes.fromhex("cd" * 32)
    keystore.store_key("wechat", "wxid_abc", key, protection="password", password="p")
    keys = keystore.list_keys()
    assert len(keys) == 1
    assert keys[0]["wxid"] == "wxid_abc"


def test_delete_key(keystore):
    key = bytes.fromhex("ef" * 32)
    keystore.store_key("wechat", "wxid_del", key, protection="password", password="p")
    keystore.delete_key("wechat", "wxid_del")
    assert keystore.list_keys() == []


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI only on Windows")
def test_store_and_retrieve_dpapi(keystore):
    key = bytes.fromhex("ab" * 32)
    keystore.store_key("wechat", "wxid_dpapi", key, protection="dpapi")
    retrieved = keystore.get_key("wechat", "wxid_dpapi")
    assert retrieved == key
