"""Session token management using pluggable secret backends."""
from __future__ import annotations

import json
import logging
import os
from base64 import b64decode, b64encode
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from wxtools.infrastructure.secrets.backends import get_backend

logger = logging.getLogger("wxtools.session")


class UnlockSession:
    def __init__(self, session_dir: Path) -> None:
        self._dir = session_dir

    def _session_path(self, plugin: str, account_id: str) -> Path:
        return self._dir / f"{plugin}_{account_id}.session"

    def create(
        self,
        plugin: str,
        account_id: str,
        key: bytes,
        ttl_minutes: int = 120,
        backend_name: str = "auto",
        password: Optional[str] = None,
    ) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

        session_fernet_key = Fernet.generate_key()
        f = Fernet(session_fernet_key)
        encrypted_key = f.encrypt(key)

        kwargs = {}
        if password:
            kwargs["password"] = password
        backend = get_backend(backend_name, **kwargs)
        scope = f"session:{plugin}:{account_id}"

        if not backend.is_available():
            if password:
                backend = get_backend("password-file", password=password)
            else:
                raise OSError(
                    f"Secret backend '{backend.name}' is not available and no password was provided. "
                    "Use password protection or install the required platform keychain."
                )

        protected_session_key = b64encode(
            backend.protect(session_fernet_key, scope=scope)
        ).decode()

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        session_data = {
            "encrypted_key": b64encode(encrypted_key).decode(),
            "session_key_protected": protected_session_key,
            "protection": backend.name,
            "expires_at": expires_at.isoformat(),
            "account": account_id,
            "plugin": plugin,
        }

        path = self._session_path(plugin, account_id)
        path.write_text(
            json.dumps(session_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            os.chmod(path, 0o600)
        except (OSError, NotImplementedError):
            pass

    def get_key(
        self,
        plugin: str,
        account_id: str,
        password: Optional[str] = None,
    ) -> Optional[bytes]:
        path = self._session_path(plugin, account_id)
        if not path.is_file():
            return None

        try:
            data = json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        expires_at = datetime.fromisoformat(data["expires_at"])
        if datetime.now(timezone.utc) >= expires_at:
            self.clear(plugin, account_id)
            return None

        protection = data.get("protection", "password-file")
        kwargs = {}
        if password:
            kwargs["password"] = password

        try:
            backend = get_backend(protection, **kwargs)
        except ValueError:
            return None

        protected_bytes = b64decode(data["session_key_protected"])
        scope = f"session:{plugin}:{account_id}"

        try:
            session_fernet_key = backend.unprotect(protected_bytes, scope=scope)
        except (OSError, Exception):
            return None

        try:
            f = Fernet(session_fernet_key)
            encrypted_key = b64decode(data["encrypted_key"])
            return f.decrypt(encrypted_key)
        except (InvalidToken, Exception):
            return None

    def clear(self, plugin: str, account_id: str) -> None:
        path = self._session_path(plugin, account_id)
        if path.is_file():
            path.unlink()

    def clear_all(self) -> None:
        if self._dir.is_dir():
            for f in self._dir.glob("*.session"):
                f.unlink()
