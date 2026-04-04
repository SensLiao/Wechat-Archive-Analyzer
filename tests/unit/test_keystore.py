import json
import sys
from unittest.mock import patch

import pytest

from wxtools.core.keystore import Keystore


@pytest.fixture
def keystore(tmp_home):
    return Keystore(keys_dir=tmp_home / "keys")


class TestKeystorePasswordBackend:
    def test_store_and_retrieve(self, keystore):
        key = bytes.fromhex("ab" * 32)
        keystore.store_key("wechat", "wxid_test", key,
                           backend_name="password-file", password="mypass")
        retrieved = keystore.get_key("wechat", "wxid_test", password="mypass")
        assert retrieved == key

    def test_wrong_password_raises(self, keystore):
        key = bytes.fromhex("ab" * 32)
        keystore.store_key("wechat", "wxid_test", key,
                           backend_name="password-file", password="correct")
        with pytest.raises(Exception):
            keystore.get_key("wechat", "wxid_test", password="wrong")

    def test_metadata_has_backend_name(self, keystore):
        key = bytes.fromhex("cd" * 32)
        keystore.store_key("wechat", "wxid_meta", key,
                           backend_name="password-file", password="p")
        keys = keystore.list_keys()
        meta = [k for k in keys if k["wxid"] == "wxid_meta"][0]
        assert meta["protection"] == "password-file"


class TestKeystoreDpapiBackend:
    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI only on Windows")
    def test_store_and_retrieve_dpapi(self, keystore):
        key = bytes.fromhex("ab" * 32)
        keystore.store_key("wechat", "wxid_dpapi", key,
                           backend_name="windows-dpapi")
        retrieved = keystore.get_key("wechat", "wxid_dpapi")
        assert retrieved == key


class TestKeystoreBackwardCompat:
    def test_reads_v1_password_format(self, keystore):
        key = bytes.fromhex("ab" * 32)
        import os
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        import base64

        salt = os.urandom(16)
        kdf = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1)
        raw = kdf.derive(b"oldpass")
        fernet_key = base64.urlsafe_b64encode(raw)
        f = Fernet(fernet_key)
        encrypted = b"\x01" + salt + f.encrypt(key)

        key_path = keystore._key_path("wechat", "wxid_compat")
        key_path.write_bytes(encrypted)
        meta = {"wxid": "wxid_compat", "plugin": "wechat", "protection": "password"}
        keystore._meta_path("wechat", "wxid_compat").write_text(
            json.dumps(meta), encoding="utf-8"
        )

        retrieved = keystore.get_key("wechat", "wxid_compat", password="oldpass")
        assert retrieved == key

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI only on Windows")
    def test_reads_v1_dpapi_format(self, keystore):
        from wxtools.core.secret_backends.dpapi import _dpapi_encrypt
        key = bytes.fromhex("ab" * 32)
        encrypted = b"\x01" + b"\x00" + _dpapi_encrypt(key)
        key_path = keystore._key_path("wechat", "wxid_compat_dpapi")
        key_path.write_bytes(encrypted)
        meta = {"wxid": "wxid_compat_dpapi", "plugin": "wechat", "protection": "dpapi"}
        keystore._meta_path("wechat", "wxid_compat_dpapi").write_text(
            json.dumps(meta), encoding="utf-8"
        )
        retrieved = keystore.get_key("wechat", "wxid_compat_dpapi")
        assert retrieved == key


class TestKeystoreLegacyParamCompat:
    """Test that callers using the old protection= keyword still work."""

    def test_store_with_protection_password(self, keystore):
        key = bytes.fromhex("ab" * 32)
        keystore.store_key("wechat", "wxid_legacy", key,
                           protection="password", password="pw")
        retrieved = keystore.get_key("wechat", "wxid_legacy", password="pw")
        assert retrieved == key

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI only on Windows")
    def test_store_with_protection_dpapi(self, keystore):
        key = bytes.fromhex("ab" * 32)
        keystore.store_key("wechat", "wxid_legacy_d", key, protection="dpapi")
        retrieved = keystore.get_key("wechat", "wxid_legacy_d")
        assert retrieved == key


class TestKeystoreManagement:
    def test_list_keys_empty(self, keystore):
        assert keystore.list_keys() == []

    def test_list_keys_after_store(self, keystore):
        key = bytes.fromhex("cd" * 32)
        keystore.store_key("wechat", "wxid_abc", key,
                           backend_name="password-file", password="p")
        keys = keystore.list_keys()
        assert len(keys) == 1
        assert keys[0]["wxid"] == "wxid_abc"

    def test_delete_key(self, keystore):
        key = bytes.fromhex("ef" * 32)
        keystore.store_key("wechat", "wxid_del", key,
                           backend_name="password-file", password="p")
        keystore.delete_key("wechat", "wxid_del")
        assert keystore.list_keys() == []

    def test_update_metadata(self, keystore):
        key = bytes.fromhex("ab" * 32)
        keystore.store_key("wechat", "wxid_meta", key,
                           backend_name="password-file", password="p")
        keystore.update_metadata("wechat", "wxid_meta",
                                  {"last_verified": "2026-04-04T00:00:00Z"})
        keys = keystore.list_keys()
        meta = [k for k in keys if k["wxid"] == "wxid_meta"][0]
        assert meta["last_verified"] == "2026-04-04T00:00:00Z"
        assert meta["protection"] == "password-file"

    def test_has_key(self, keystore):
        assert keystore.has_key("wechat", "wxid_test") is False
        keystore.store_key("wechat", "wxid_test", b"x" * 32,
                           backend_name="password-file", password="p")
        assert keystore.has_key("wechat", "wxid_test") is True

    def test_update_metadata_no_file(self, keystore):
        keystore.update_metadata("wechat", "wxid_nonexist", {"foo": "bar"})
