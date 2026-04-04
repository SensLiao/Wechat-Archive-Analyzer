"""Encrypted key storage with pluggable secret backends."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from wxtools.core.errors import KeyNotFoundError, KeyPasswordWrongError
from wxtools.core.secret_backends import get_backend

_VERSION_LEGACY = b"\x01"
_VERSION_V2 = b"\x02"


class Keystore:
    def __init__(self, keys_dir: Path):
        self._dir = Path(keys_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, plugin: str, account_id: str) -> Path:
        return self._dir / f"{plugin}_{account_id}.key"

    def _meta_path(self, plugin: str, account_id: str) -> Path:
        return self._dir / f"{plugin}_{account_id}.json"

    def has_key(self, plugin: str, account_id: str) -> bool:
        return self._key_path(plugin, account_id).exists()

    def store_key(
        self,
        plugin: str,
        account_id: str,
        key: bytes,
        backend_name: str = "auto",
        password: Optional[str] = None,
        # Legacy alias — callers may still pass protection="dpapi"|"password"
        protection: Optional[str] = None,
    ) -> None:
        # Legacy callers pass protection= instead of backend_name=
        if protection is not None and backend_name == "auto":
            backend_name = _normalize_backend_name(protection)
        else:
            backend_name = _normalize_backend_name(backend_name)

        kwargs: Dict[str, Any] = {}
        if password:
            kwargs["password"] = password

        backend = get_backend(backend_name, **kwargs)
        scope = f"keystore:{plugin}:{account_id}"
        ciphertext = backend.protect(key, scope=scope)

        # v2 on-disk format: VERSION + name_len(1 byte) + name + ciphertext
        name_bytes = backend.name.encode("utf-8")
        stored = _VERSION_V2 + bytes([len(name_bytes)]) + name_bytes + ciphertext
        self._key_path(plugin, account_id).write_bytes(stored)

        meta: Dict[str, Any] = {
            "wxid": account_id,
            "plugin": plugin,
            "protection": backend.name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_verified": datetime.now(timezone.utc).isoformat(),
        }
        self._meta_path(plugin, account_id).write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    def get_key(
        self,
        plugin: str,
        account_id: str,
        password: Optional[str] = None,
    ) -> bytes:
        key_path = self._key_path(plugin, account_id)
        if not key_path.exists():
            raise KeyNotFoundError(account_id)
        data = key_path.read_bytes()
        version = data[0:1]

        if version == _VERSION_V2:
            return self._read_v2(data, plugin, account_id, password)
        elif version == _VERSION_LEGACY:
            return self._read_v1_legacy(data, password)
        else:
            raise ValueError(f"Unsupported keystore version: {version!r}")

    def _read_v2(
        self, data: bytes, plugin: str, account_id: str,
        password: Optional[str],
    ) -> bytes:
        name_len = data[1]
        name = data[2:2 + name_len].decode("utf-8")
        ciphertext = data[2 + name_len:]

        kwargs: Dict[str, Any] = {}
        if password:
            kwargs["password"] = password

        backend = get_backend(name, **kwargs)
        scope = f"keystore:{plugin}:{account_id}"
        return backend.unprotect(ciphertext, scope=scope)

    def _read_v1_legacy(self, data: bytes, password: Optional[str]) -> bytes:
        """Read old v1 format for backward compatibility."""
        marker = data[1:2]
        if marker == b"\x00":
            # v1 DPAPI
            backend = get_backend("windows-dpapi")
            return backend.unprotect(data[2:], scope="legacy")
        else:
            # v1 password (salt + fernet token)
            if not password:
                raise KeyPasswordWrongError()
            salt = data[1:1 + 16]
            token = data[1 + 16:]
            import base64
            from cryptography.fernet import Fernet, InvalidToken
            from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
            kdf = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1)
            raw = kdf.derive(password.encode("utf-8"))
            fernet_key = base64.urlsafe_b64encode(raw)
            f = Fernet(fernet_key)
            try:
                return f.decrypt(token)
            except InvalidToken:
                raise KeyPasswordWrongError()

    def delete_key(self, plugin: str, account_id: str) -> None:
        key_path = self._key_path(plugin, account_id)
        meta_path = self._meta_path(plugin, account_id)
        if key_path.exists():
            key_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

    def update_metadata(self, plugin: str, account_id: str, updates: Dict[str, Any]) -> None:
        meta_path = self._meta_path(plugin, account_id)
        if not meta_path.exists():
            return
        meta = json.loads(meta_path.read_text("utf-8"))
        meta.update(updates)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_keys(self) -> List[Dict[str, Any]]:
        keys: List[Dict[str, Any]] = []
        for meta_file in sorted(self._dir.glob("*.json")):
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                keys.append(meta)
            except (json.JSONDecodeError, KeyError):
                continue
        return keys


def _normalize_backend_name(name: str) -> str:
    """Map legacy protection values to backend names."""
    legacy_map = {
        "dpapi": "windows-dpapi",
        "password": "password-file",
    }
    return legacy_map.get(name, name)
