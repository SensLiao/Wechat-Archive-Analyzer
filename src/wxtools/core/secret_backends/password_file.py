"""Password-based secret protection using Fernet + scrypt. Works on all platforms."""
from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

_SCRYPT_N = 2**17
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_KEY_LEN = 32
_SALT_LEN = 16


def _derive_fernet_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from *password* and *salt* via scrypt."""
    kdf = Scrypt(
        salt=salt, length=_SCRYPT_KEY_LEN, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    raw = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


class PasswordFileBackend:
    """Fernet+scrypt secret backend — universal fallback for all platforms."""

    def __init__(self, password: str) -> None:
        if not password:
            raise ValueError("Password must not be empty")
        self._password = password

    @property
    def name(self) -> str:
        return "password-file"

    def is_available(self) -> bool:
        return True

    def protect(self, plaintext: bytes, *, scope: str) -> bytes:
        """Encrypt *plaintext* with a random salt. Returns ``salt || fernet_token``."""
        salt = os.urandom(_SALT_LEN)
        fernet_key = _derive_fernet_key(self._password, salt)
        f = Fernet(fernet_key)
        return salt + f.encrypt(plaintext)

    def unprotect(self, ciphertext: bytes, *, scope: str) -> bytes:
        """Decrypt *ciphertext* (``salt || fernet_token``)."""
        salt = ciphertext[:_SALT_LEN]
        token = ciphertext[_SALT_LEN:]
        fernet_key = _derive_fernet_key(self._password, salt)
        f = Fernet(fernet_key)
        try:
            return f.decrypt(token)
        except InvalidToken:
            from wxtools.core.errors import KeyPasswordWrongError

            raise KeyPasswordWrongError()
