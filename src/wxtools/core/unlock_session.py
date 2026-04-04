"""Session token management for password-protected key access."""
from __future__ import annotations

import json
import logging
import os
import sys
from base64 import b64decode, b64encode
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("wxtools.session")


class UnlockSession:
    def __init__(self, session_dir: Path) -> None:
        self._dir = session_dir

    def _session_path(self, plugin: str, account_id: str) -> Path:
        return self._dir / f"{plugin}_{account_id}.session"

    def create(self, plugin: str, account_id: str, key: bytes, ttl_minutes: int = 120) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        session_fernet_key = Fernet.generate_key()
        f = Fernet(session_fernet_key)
        encrypted_key = f.encrypt(key)

        if sys.platform == "win32":
            try:
                from wxtools.core.keystore import _dpapi_encrypt
                protected_session_key = b64encode(_dpapi_encrypt(session_fernet_key)).decode()
                protection = "dpapi"
            except OSError:
                protected_session_key = b64encode(session_fernet_key).decode()
                protection = "file"
        else:
            protected_session_key = b64encode(session_fernet_key).decode()
            protection = "file"

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        session_data = {
            "encrypted_key": b64encode(encrypted_key).decode(),
            "session_key_protected": protected_session_key,
            "protection": protection,
            "expires_at": expires_at.isoformat(),
            "account": account_id,
            "plugin": plugin,
        }

        path = self._session_path(plugin, account_id)
        path.write_text(json.dumps(session_data, ensure_ascii=False, indent=2), encoding="utf-8")
        if sys.platform != "win32":
            os.chmod(path, 0o600)

    def get_key(self, plugin: str, account_id: str) -> Optional[bytes]:
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

        protected_bytes = b64decode(data["session_key_protected"])
        if data.get("protection") == "dpapi" and sys.platform == "win32":
            try:
                from wxtools.core.keystore import _dpapi_decrypt
                session_fernet_key = _dpapi_decrypt(protected_bytes)
            except OSError:
                return None
        else:
            session_fernet_key = protected_bytes

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
