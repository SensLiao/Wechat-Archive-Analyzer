"""Tests for secret backend implementations."""
import sys

import pytest

from wxtools.infrastructure.secrets.backends.base import SecretBackend
from wxtools.infrastructure.secrets.backends.dpapi import DpapiBackend
from wxtools.infrastructure.secrets.backends.password_file import PasswordFileBackend


class TestPasswordFileBackend:
    def test_implements_protocol(self):
        backend = PasswordFileBackend(password="test123")
        assert isinstance(backend, SecretBackend)

    def test_name(self):
        backend = PasswordFileBackend(password="test123")
        assert backend.name == "password-file"

    def test_is_available(self):
        backend = PasswordFileBackend(password="test123")
        assert backend.is_available() is True

    def test_roundtrip(self):
        backend = PasswordFileBackend(password="mysecret")
        plaintext = b"hello world secret key data"
        ciphertext = backend.protect(plaintext, scope="keystore:wechat:wxid_test")
        recovered = backend.unprotect(ciphertext, scope="keystore:wechat:wxid_test")
        assert recovered == plaintext

    def test_wrong_password_fails(self):
        b1 = PasswordFileBackend(password="correct")
        ciphertext = b1.protect(b"secret", scope="test")
        b2 = PasswordFileBackend(password="wrong")
        with pytest.raises(Exception):
            b2.unprotect(ciphertext, scope="test")

    def test_no_password_raises(self):
        with pytest.raises(ValueError, match="[Pp]assword"):
            PasswordFileBackend(password="")


class TestDpapiBackend:
    def test_implements_protocol(self):
        backend = DpapiBackend()
        assert isinstance(backend, SecretBackend)

    def test_name(self):
        assert DpapiBackend().name == "windows-dpapi"

    def test_is_available_matches_platform(self):
        backend = DpapiBackend()
        if sys.platform == "win32":
            assert backend.is_available() is True
        else:
            assert backend.is_available() is False

    @pytest.mark.skipif(sys.platform != "win32", reason="DPAPI only on Windows")
    def test_roundtrip(self):
        backend = DpapiBackend()
        plaintext = b"dpapi secret data for testing"
        ciphertext = backend.protect(plaintext, scope="keystore:wechat:wxid_test")
        recovered = backend.unprotect(ciphertext, scope="keystore:wechat:wxid_test")
        assert recovered == plaintext


# ---------------------------------------------------------------------------
# macOS Keychain backend
# ---------------------------------------------------------------------------
from unittest.mock import patch  # noqa: E402

from wxtools.infrastructure.secrets.backends.macos_keychain import MacosKeychainBackend  # noqa: E402


class TestMacosKeychainBackend:
    def test_implements_protocol(self):
        backend = MacosKeychainBackend()
        assert isinstance(backend, SecretBackend)

    def test_name(self):
        assert MacosKeychainBackend().name == "macos-keychain"

    def test_is_available_false_on_non_mac(self):
        with patch("sys.platform", "win32"):
            assert MacosKeychainBackend().is_available() is False

    def test_roundtrip_mocked(self):
        backend = MacosKeychainBackend()
        stored_passwords: dict[tuple[str, str], bytes] = {}

        def mock_store(service, account, password_bytes):
            stored_passwords[(service, account)] = password_bytes

        def mock_retrieve(service, account):
            return stored_passwords.get((service, account))

        def mock_delete(service, account):
            stored_passwords.pop((service, account), None)

        with patch.object(backend, "_store_to_keychain", side_effect=mock_store), \
             patch.object(backend, "_retrieve_from_keychain", side_effect=mock_retrieve), \
             patch.object(backend, "_delete_from_keychain", side_effect=mock_delete), \
             patch.object(backend, "is_available", return_value=True):
            plaintext = b"keychain test secret"
            ciphertext = backend.protect(plaintext, scope="keystore:wechat:wxid_test")
            recovered = backend.unprotect(ciphertext, scope="keystore:wechat:wxid_test")
            assert recovered == plaintext


# ---------------------------------------------------------------------------
# Linux Secret Service backend
# ---------------------------------------------------------------------------
from wxtools.infrastructure.secrets.backends.linux_secret_service import LinuxSecretServiceBackend  # noqa: E402


class TestLinuxSecretServiceBackend:
    def test_implements_protocol(self):
        backend = LinuxSecretServiceBackend()
        assert isinstance(backend, SecretBackend)

    def test_name(self):
        assert LinuxSecretServiceBackend().name == "linux-secret-service"

    def test_is_available_false_on_non_linux(self):
        with patch("sys.platform", "win32"):
            assert LinuxSecretServiceBackend().is_available() is False

    def test_roundtrip_mocked(self):
        backend = LinuxSecretServiceBackend()
        stored: dict[tuple, bytes] = {}

        def mock_store(label, attributes, secret_bytes):
            key = tuple(sorted(attributes.items()))
            stored[key] = secret_bytes

        def mock_retrieve(attributes):
            key = tuple(sorted(attributes.items()))
            return stored.get(key)

        def mock_delete(attributes):
            key = tuple(sorted(attributes.items()))
            stored.pop(key, None)

        with patch.object(backend, "_store_secret", side_effect=mock_store), \
             patch.object(backend, "_retrieve_secret", side_effect=mock_retrieve), \
             patch.object(backend, "_delete_secret", side_effect=mock_delete), \
             patch.object(backend, "is_available", return_value=True):
            plaintext = b"linux secret service test"
            ciphertext = backend.protect(plaintext, scope="keystore:wechat:wxid_test")
            recovered = backend.unprotect(ciphertext, scope="keystore:wechat:wxid_test")
            assert recovered == plaintext


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------
from wxtools.infrastructure.secrets.backends import get_backend, list_backends  # noqa: E402


class TestBackendFactory:
    def test_get_password_file_backend(self):
        backend = get_backend("password-file", password="testpass")
        assert backend.name == "password-file"

    def test_get_windows_dpapi_backend(self):
        backend = get_backend("windows-dpapi")
        assert backend.name == "windows-dpapi"

    def test_get_macos_keychain_backend(self):
        backend = get_backend("macos-keychain")
        assert backend.name == "macos-keychain"

    def test_get_linux_secret_service_backend(self):
        backend = get_backend("linux-secret-service")
        assert backend.name == "linux-secret-service"

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            get_backend("nonexistent")

    def test_list_backends_returns_all(self):
        names = list_backends()
        assert "windows-dpapi" in names
        assert "password-file" in names
        assert "macos-keychain" in names
        assert "linux-secret-service" in names

    def test_get_auto_selects_platform_default(self):
        backend = get_backend("auto")
        assert backend.name in ("windows-dpapi", "macos-keychain", "linux-secret-service")
