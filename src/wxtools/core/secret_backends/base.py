"""SecretBackend protocol — the interface all backends implement."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretBackend(Protocol):
    """Encrypt/decrypt secret bytes using a platform-specific mechanism."""

    @property
    def name(self) -> str:
        """Backend identifier stored in metadata, e.g. 'windows-dpapi'."""
        ...

    def is_available(self) -> bool:
        """Return True if this backend can operate on the current platform."""
        ...

    def protect(self, plaintext: bytes, *, scope: str) -> bytes:
        """Encrypt *plaintext*. *scope* is a hint like 'keystore:wechat:wxid_xxx'."""
        ...

    def unprotect(self, ciphertext: bytes, *, scope: str) -> bytes:
        """Decrypt *ciphertext*."""
        ...
