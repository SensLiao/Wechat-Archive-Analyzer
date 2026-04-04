"""Decrypt WeChat SQLCipher databases using derived encryption keys.

WeChat 4.x uses SQLCipher 4 with AES-256-CBC, PBKDF2-SHA512, HMAC-SHA512.
Each database has a unique salt (first 16 bytes) and thus a unique derived key.
This module performs direct AES-CBC decryption using per-DB derived keys,
bypassing the need for the sqlcipher CLI or the raw pre-PBKDF2 key.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import logging
import os
import shutil
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from wxtools.core.errors import DbDecryptFailedError, DbNotFoundError

logger = logging.getLogger("wxtools.decryptor")

PAGE_SIZE = 4096
SALT_SIZE = 16
IV_SIZE = 16
HMAC_SIZE = 64  # SHA-512
RESERVE_SIZE = IV_SIZE + HMAC_SIZE  # 80 bytes
KEY_SIZE = 32
SQLITE_HEADER = b"SQLite format 3\x00"


def _needs_redecrypt(source: Path, cache: Path) -> bool:
    if not cache.exists():
        return True
    return source.stat().st_mtime > cache.stat().st_mtime


def _decrypt_page(page: bytes, page_num: int, enc_key: bytes) -> bytes:
    """Decrypt a single SQLCipher page."""
    from Crypto.Cipher import AES

    reserve_start = PAGE_SIZE - RESERVE_SIZE  # 4016
    iv = page[reserve_start : reserve_start + IV_SIZE]

    offset = SALT_SIZE if page_num == 0 else 0
    encrypted = page[offset:reserve_start]

    cipher = AES.new(enc_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted)

    result = bytearray(PAGE_SIZE)
    if page_num == 0:
        result[0:16] = SQLITE_HEADER
        result[16:reserve_start] = decrypted
        # Keep reserved_space = RESERVE_SIZE (80) at offset 20.
        # The B-tree data was laid out for 4016-byte usable pages,
        # so SQLite must use the same usable size to read correctly.
        result[20] = RESERVE_SIZE
    else:
        result[0:reserve_start] = decrypted
    # Last 80 bytes stay as zeros (no longer needed for IV/HMAC)

    return bytes(result)


def _decrypt_db_file(source: Path, dest: Path, enc_key_hex: str) -> None:
    """Decrypt a single SQLCipher database file."""
    enc_key = bytes.fromhex(enc_key_hex)

    with open(source, "rb") as f:
        data = f.read()

    file_size = len(data)
    if file_size < PAGE_SIZE:
        raise DbDecryptFailedError()

    total_pages = file_size // PAGE_SIZE

    with open(dest, "wb") as out:
        for page_num in range(total_pages):
            page_start = page_num * PAGE_SIZE
            page = data[page_start : page_start + PAGE_SIZE]
            out.write(_decrypt_page(page, page_num, enc_key))

    logger.info("Decrypted %s (%d pages)", source.name, total_pages)


class Decryptor:
    def __init__(self, sqlcipher_path: str = "sqlcipher"):
        # sqlcipher_path kept for backward compatibility but unused
        pass

    def decrypt_all(
        self,
        source_dir: Path,
        cache_dir: Path,
        key_data: str,
        db_patterns: Optional[List[str]] = None,
    ) -> List[Path]:
        """Decrypt all databases using per-DB derived keys.

        Args:
            source_dir: Directory containing encrypted .db files
            cache_dir: Output directory for decrypted files
            key_data: JSON-encoded dict of {rel_path: hex_key}, or a single hex key
            db_patterns: Unused, kept for backward compatibility
        """
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Parse key_data: either a JSON dict or a single hex key
        keys = _parse_key_data(key_data, source_dir)

        decrypted: List[Path] = []
        db_meta_entries: List[Dict[str, Any]] = []

        for rel_path, key_hex in keys.items():
            source_db = source_dir / rel_path
            if not source_db.exists():
                logger.warning("Source DB not found: %s", source_db)
                continue

            cache_db = cache_dir / rel_path
            cache_db.parent.mkdir(parents=True, exist_ok=True)

            if _needs_redecrypt(source_db, cache_db):
                logger.info("Decrypting %s", rel_path)
                try:
                    self._snapshot_and_decrypt(source_db, cache_db, key_hex)
                    decrypted.append(cache_db)
                    db_meta_entries.append(_build_db_meta(rel_path, source_db))
                except Exception:
                    logger.exception("Failed to decrypt %s", rel_path)
            else:
                logger.info("Cache up-to-date: %s", rel_path)
                decrypted.append(cache_db)
                db_meta_entries.append(_build_db_meta(rel_path, source_db))

        # Write cache metadata
        _write_cache_meta(cache_dir, db_meta_entries)

        return decrypted

    def _snapshot_and_decrypt(self, source: Path, dest: Path, key_hex: str) -> None:
        """Copy source DB to temp dir, decrypt, then atomically move to dest."""
        with tempfile.TemporaryDirectory(prefix="wxtools_") as tmpdir:
            tmp_source = Path(tmpdir) / source.name
            shutil.copy2(source, tmp_source)

            tmp_dest = Path(tmpdir) / f"{source.stem}_plain.db"
            _decrypt_db_file(tmp_source, tmp_dest, key_hex)

            dest_tmp = dest.with_suffix(".tmp")
            shutil.move(str(tmp_dest), str(dest_tmp))
            os.replace(str(dest_tmp), str(dest))


def _build_db_meta(rel_path: str, source_db: Path) -> Dict[str, Any]:
    """Build metadata entry for a single decrypted database."""
    st = source_db.stat()
    return {
        "source": rel_path,
        "source_mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        "size_bytes": st.st_size,
        "decrypted_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def _write_cache_meta(cache_dir: Path, db_entries: List[Dict[str, Any]]) -> None:
    """Write .cache_meta.json to the cache directory."""
    meta = {
        "version": 1,
        "decrypted_at": datetime.now(tz=timezone.utc).isoformat(),
        "databases": db_entries,
    }
    meta_path = cache_dir / ".cache_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_key_data(key_data: str, source_dir: Path) -> Dict[str, str]:
    """Parse key_data as JSON dict or single hex key."""
    # Try JSON dict first
    try:
        keys = json.loads(key_data)
        if isinstance(keys, dict):
            return keys
    except (json.JSONDecodeError, TypeError):
        pass

    # Single hex key — scan source_dir for all .db files and apply same key
    if len(key_data) == 64:
        keys = {}
        for root, _dirs, files in os.walk(source_dir):
            for f in files:
                if f.endswith(".db"):
                    rel = os.path.relpath(os.path.join(root, f), source_dir)
                    keys[rel] = key_data
        return keys

    raise DbDecryptFailedError()
