"""Fast key validation using HMAC-SHA512 against DB first page."""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import logging
import struct
from pathlib import Path
from typing import Dict

logger = logging.getLogger("wxtools.key_validator")

PAGE_SIZE = 4096
SALT_SIZE = 16
KEY_SIZE = 32
RESERVE_SIZE = 80


def _load_db_info(db_path: Path) -> dict:
    raw = db_path.read_bytes()
    if len(raw) < PAGE_SIZE:
        raise ValueError(f"文件太小，不是有效的数据库: {db_path}")
    page = raw[:PAGE_SIZE]
    salt = page[:SALT_SIZE]
    hmac_salt = bytes(a ^ 0x3A for a in salt)
    content_end = PAGE_SIZE - RESERVE_SIZE
    encrypted_content = page[SALT_SIZE:content_end]
    reserve_start = content_end
    hmac_stored = page[reserve_start + 16 : reserve_start + 16 + 64]
    return {
        "hmac_salt": hmac_salt,
        "hmac_input": encrypted_content,
        "hmac_stored": hmac_stored,
    }


def validate_key_for_db(key_hex: str, db_path: Path) -> bool:
    try:
        db_info = _load_db_info(db_path)
    except (ValueError, OSError) as e:
        logger.warning("无法读取数据库文件 %s: %s", db_path, e)
        return False
    enc_key = bytes.fromhex(key_hex)
    hmac_key = hashlib.pbkdf2_hmac(
        "sha512", enc_key, db_info["hmac_salt"], 2, KEY_SIZE
    )
    h = hmac_mod.new(hmac_key, db_info["hmac_input"], hashlib.sha512)
    h.update(struct.pack("<I", 1))
    return hmac_mod.compare_digest(h.digest(), db_info["hmac_stored"])


def validate_key_for_account(key_data: str, db_dir: Path) -> Dict[str, int]:
    key_data = key_data.strip()
    if key_data.startswith("{"):
        key_map: Dict[str, str] = json.loads(key_data)
    else:
        key_map = {}
        for db_file in sorted(db_dir.rglob("*.db")):
            rel = str(db_file.relative_to(db_dir)).replace("\\", "/")
            key_map[rel] = key_data
    total = 0
    passed = 0
    details = []
    for rel_path, key_hex in key_map.items():
        db_path = db_dir / rel_path
        if not db_path.exists():
            continue
        total += 1
        ok = validate_key_for_db(key_hex, db_path)
        if ok:
            passed += 1
        details.append({"path": rel_path, "ok": ok})
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "details": details,
    }
