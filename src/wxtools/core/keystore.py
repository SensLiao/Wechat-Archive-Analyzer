"""Encrypted key storage with DPAPI and Fernet/scrypt backends."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from wxtools.core.errors import KeyNotFoundError, KeyPasswordWrongError

_SCRYPT_N = 2**17
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_KEY_LEN = 32
_SALT_LEN = 16
_VERSION = b"\x01"


def _derive_fernet_key(password: str, salt: bytes) -> bytes:
    import base64
    kdf = Scrypt(salt=salt, length=_SCRYPT_KEY_LEN, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    raw = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


def _dpapi_encrypt(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    input_blob = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    output_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)
    ):
        raise OSError("DPAPI CryptProtectData failed")
    encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
    ctypes.windll.kernel32.LocalFree(output_blob.pbData)
    return encrypted


def _dpapi_decrypt(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    input_blob = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    output_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)
    ):
        raise OSError("DPAPI CryptUnprotectData failed")
    decrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
    ctypes.windll.kernel32.LocalFree(output_blob.pbData)
    return decrypted


class Keystore:
    def __init__(self, keys_dir: Path):
        self._dir = Path(keys_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, plugin: str, account_id: str) -> Path:
        return self._dir / f"{plugin}_{account_id}.key"

    def _meta_path(self, plugin: str, account_id: str) -> Path:
        return self._dir / f"{plugin}_{account_id}.json"

    def has_key(self, plugin: str, account_id: str) -> bool:
        """Check whether a key file already exists for this plugin/account."""
        return self._key_path(plugin, account_id).exists()

    def store_key(
        self,
        plugin: str,
        account_id: str,
        key: bytes,
        protection: str = "dpapi",
        password: Optional[str] = None,
    ) -> None:
        if protection == "password":
            if not password:
                raise ValueError("Password required for password protection mode")
            salt = os.urandom(_SALT_LEN)
            fernet_key = _derive_fernet_key(password, salt)
            f = Fernet(fernet_key)
            encrypted = _VERSION + salt + f.encrypt(key)
        elif protection == "dpapi":
            if sys.platform != "win32":
                raise OSError("DPAPI only available on Windows")
            encrypted = _VERSION + b"\x00" + _dpapi_encrypt(key)
        else:
            raise ValueError(f"Unknown protection mode: {protection}")

        self._key_path(plugin, account_id).write_bytes(encrypted)
        meta: Dict[str, Any] = {
            "wxid": account_id,
            "plugin": plugin,
            "protection": protection,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_verified": datetime.now(timezone.utc).isoformat(),
        }
        self._meta_path(plugin, account_id).write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    def get_key(self, plugin: str, account_id: str, password: Optional[str] = None) -> bytes:
        key_path = self._key_path(plugin, account_id)
        if not key_path.exists():
            raise KeyNotFoundError(account_id)
        data = key_path.read_bytes()
        version = data[0:1]
        if version != _VERSION:
            raise ValueError(f"Unsupported keystore version: {version!r}")
        marker = data[1:2]
        if marker == b"\x00":
            return _dpapi_decrypt(data[2:])
        else:
            salt = data[1:1 + _SALT_LEN]
            token = data[1 + _SALT_LEN:]
            if not password:
                raise KeyPasswordWrongError()
            fernet_key = _derive_fernet_key(password, salt)
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
        """Merge *updates* into existing metadata JSON."""
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
