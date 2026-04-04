"""Linux Secret Service backend using secret-tool CLI."""
from __future__ import annotations

import base64
import subprocess
import sys

from cryptography.fernet import Fernet, InvalidToken

_APP_ID = "com.wxtools"


class LinuxSecretServiceBackend:
    """Protect secrets via the Linux Secret Service (libsecret / secret-tool).

    Strategy mirrors the macOS Keychain backend: a Fernet wrapping key is
    stored in the Secret Service and used to encrypt/decrypt data locally.
    """

    @property
    def name(self) -> str:
        return "linux-secret-service"

    def is_available(self) -> bool:
        if sys.platform != "linux":
            return False
        try:
            result = subprocess.run(
                ["secret-tool", "--help"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode in (0, 1)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def protect(self, plaintext: bytes, *, scope: str) -> bytes:
        if not self.is_available():
            raise OSError("Secret Service is not available on this platform")
        fernet_key = Fernet.generate_key()
        f = Fernet(fernet_key)
        encrypted = f.encrypt(plaintext)
        attrs = {"application": _APP_ID, "scope": scope, "type": "wrapping-key"}
        self._store_secret(f"wxtools:{scope}", attrs, fernet_key)
        return encrypted

    def unprotect(self, ciphertext: bytes, *, scope: str) -> bytes:
        if not self.is_available():
            raise OSError("Secret Service is not available on this platform")
        attrs = {"application": _APP_ID, "scope": scope, "type": "wrapping-key"}
        fernet_key = self._retrieve_secret(attrs)
        if fernet_key is None:
            raise OSError(f"No Secret Service entry found for scope '{scope}'")
        f = Fernet(fernet_key)
        try:
            return f.decrypt(ciphertext)
        except InvalidToken:
            raise OSError(
                "Failed to decrypt — Secret Service wrapping key may have changed"
            )

    # -- internal helpers wrapping secret-tool CLI -------------------------

    def _store_secret(
        self, label: str, attributes: dict, secret_bytes: bytes
    ) -> None:
        self._delete_secret(attributes)
        attr_args: list[str] = []
        for k, v in sorted(attributes.items()):
            attr_args.extend([k, v])
        pw_str = base64.urlsafe_b64encode(secret_bytes).decode("ascii")
        subprocess.run(
            ["secret-tool", "store", "--label", label] + attr_args,
            input=pw_str.encode(),
            capture_output=True,
            check=True,
            timeout=10,
        )

    def _retrieve_secret(self, attributes: dict) -> bytes | None:
        attr_args: list[str] = []
        for k, v in sorted(attributes.items()):
            attr_args.extend([k, v])
        result = subprocess.run(
            ["secret-tool", "lookup"] + attr_args,
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return base64.urlsafe_b64decode(result.stdout.strip())

    def _delete_secret(self, attributes: dict) -> None:
        attr_args: list[str] = []
        for k, v in sorted(attributes.items()):
            attr_args.extend([k, v])
        subprocess.run(
            ["secret-tool", "clear"] + attr_args,
            capture_output=True,
            timeout=10,
        )
