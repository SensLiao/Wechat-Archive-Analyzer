"""Tests for secret backend implementations."""
import pytest

from wxtools.core.secret_backends.base import SecretBackend
from wxtools.core.secret_backends.password_file import PasswordFileBackend


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
