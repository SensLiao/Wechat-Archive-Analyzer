"""macOS Keychain secret protection backend."""
from __future__ import annotations

import base64
import subprocess
import sys

from cryptography.fernet import Fernet, InvalidToken

_SERVICE_PREFIX = "com.wxtools"


class MacosKeychainBackend:
    """Protect secrets via macOS Keychain + local Fernet wrapping."""

    @property
    def name(self) -> str:
        return "macos-keychain"

    def is_available(self) -> bool:
        if sys.platform != "darwin":
            return False
        try:
            subprocess.run(["security", "help"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def protect(self, plaintext: bytes, *, scope: str) -> bytes:
        if not self.is_available():
            raise OSError("macOS Keychain is not available on this platform")
        fernet_key = Fernet.generate_key()
        f = Fernet(fernet_key)
        encrypted = f.encrypt(plaintext)
        service = f"{_SERVICE_PREFIX}.{scope}"
        self._store_to_keychain(service, "wrapping-key", fernet_key)
        return encrypted

    def unprotect(self, ciphertext: bytes, *, scope: str) -> bytes:
        if not self.is_available():
            raise OSError("macOS Keychain is not available on this platform")
        service = f"{_SERVICE_PREFIX}.{scope}"
        fernet_key = self._retrieve_from_keychain(service, "wrapping-key")
        if fernet_key is None:
            raise OSError(f"No Keychain entry found for scope '{scope}'")
        f = Fernet(fernet_key)
        try:
            return f.decrypt(ciphertext)
        except InvalidToken:
            raise OSError("Failed to decrypt — Keychain wrapping key may have changed")

    # -- low-level Keychain helpers ------------------------------------------

    def _store_to_keychain(
        self, service: str, account: str, password_bytes: bytes
    ) -> None:
        self._delete_from_keychain(service, account)
        pw_str = base64.urlsafe_b64encode(password_bytes).decode("ascii")
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-s",
                service,
                "-a",
                account,
                "-w",
                pw_str,
                "-U",
            ],
            capture_output=True,
            check=True,
            timeout=10,
        )

    def _retrieve_from_keychain(self, service: str, account: str) -> bytes | None:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                service,
                "-a",
                account,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        return base64.urlsafe_b64decode(result.stdout.strip())

    def _delete_from_keychain(self, service: str, account: str) -> None:
        subprocess.run(
            ["security", "delete-generic-password", "-s", service, "-a", account],
            capture_output=True,
            timeout=10,
        )
