"""Extract SQLCipher derived encryption keys from WeChat process memory.

WeChat 4.x uses SQLCipher 4 with per-DB salts, meaning each database has
a unique derived encryption key. This module scans the WeChat process memory
for 32-byte candidates and verifies them via fast HMAC-SHA512 check against
each database's salt (from the first page).

Platform-specific memory scanning is delegated to memory_scanner/.
Verification logic (HMAC-SHA512) is fully platform-independent.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import logging
import os
import struct
import sys
import time
from typing import Callable, Dict, Optional, Set

import psutil

from wxtools.core.errors import AdminRequiredError, WeChatNotRunningError

logger = logging.getLogger("wxtools.key_extractor")

# Per-platform WeChat process names
_PROCESS_NAMES: Dict[str, set] = {
    "win32": {"Weixin.exe", "WeChat.exe"},
    "darwin": {"WeChat"},
}

# SQLCipher 4 parameters for WeChat 4.x
PAGE_SIZE = 4096
SALT_SIZE = 16
IV_SIZE = 16
HMAC_SIZE = 64  # SHA-512
RESERVE_SIZE = IV_SIZE + HMAC_SIZE  # 80 bytes
KEY_SIZE = 32
KDF_ITER = 256000


def find_wechat_pid() -> int:
    """Find the main WeChat process (largest RSS)."""
    names = _PROCESS_NAMES.get(sys.platform, set())
    if not names:
        raise OSError(f"WeChat process discovery not supported on {sys.platform}")
    candidates = []
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] in names:
            try:
                rss = proc.memory_info().rss
                candidates.append((proc.info["pid"], rss))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                candidates.append((proc.info["pid"], 0))
    if not candidates:
        raise WeChatNotRunningError()
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


# DBs whose keys are not stored in local process memory (e.g. server-side only)
_SKIP_DBS = {"favorite/favorite.db"}


def _load_db_verification_data(db_dir: str) -> Dict[str, dict]:
    """Load salt and HMAC data from all DB files for verification."""
    dbs = {}
    for root, _dirs, files in os.walk(db_dir):
        for f in files:
            if not f.endswith(".db"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, db_dir).replace("\\", "/")
            if rel in _SKIP_DBS:
                continue
            try:
                with open(path, "rb") as fh:
                    page1 = fh.read(PAGE_SIZE)
            except OSError:
                continue
            if len(page1) < PAGE_SIZE:
                continue
            salt = page1[:SALT_SIZE]
            hmac_salt = bytes([(b ^ 0x3A) for b in salt])
            # HMAC covers encrypted data + IV: page1[16:4032]
            hmac_input = page1[SALT_SIZE : PAGE_SIZE - HMAC_SIZE]
            hmac_stored = page1[PAGE_SIZE - HMAC_SIZE : PAGE_SIZE]
            dbs[rel] = {
                "path": path,
                "salt": salt,
                "hmac_salt": hmac_salt,
                "hmac_input": hmac_input,
                "hmac_stored": hmac_stored,
            }
    return dbs


def _verify_enc_key_for_db(enc_key: bytes, db_info: dict) -> bool:
    """Verify a candidate derived key via HMAC-SHA512 check. Very fast (~microseconds)."""
    hmac_key = hashlib.pbkdf2_hmac("sha512", enc_key, db_info["hmac_salt"], 2, KEY_SIZE)
    h = hmac_mod.new(hmac_key, db_info["hmac_input"], hashlib.sha512)
    h.update(struct.pack("<I", 1))  # page number
    return h.digest() == db_info["hmac_stored"]


def extract_keys(
    db_dir: str,
    pid: Optional[int] = None,
    progress_fn: Optional[Callable[[str], None]] = None,
) -> Dict[str, str]:
    """Extract derived encryption keys for all DBs in db_dir.

    Returns a dict mapping relative DB path to hex-encoded derived key.
    """
    from wxtools.plugins.wechat.memory_scanner import get_scanner

    if pid is None:
        pid = find_wechat_pid()

    dbs = _load_db_verification_data(db_dir)
    if not dbs:
        raise RuntimeError(f"No DB files found in {db_dir}")

    logger.info("Scanning WeChat PID=%d for %d database keys", pid, len(dbs))
    if progress_fn:
        progress_fn(f"Scanning WeChat process (PID {pid}) for {len(dbs)} database keys...")

    scanner = get_scanner()
    scanner.open(pid)

    try:
        seen: Set[bytes] = set()
        found: Dict[str, str] = {}
        remaining = set(dbs.keys())
        tested = 0
        t_start = time.time()

        for region_data in scanner.readable_regions():
            if not remaining:
                break

            for off in range(0, len(region_data) - 8, 8):
                ptr = int.from_bytes(region_data[off : off + 8], "little")
                if not (0x10000 < ptr < 0x7FFFFFFFFFFFFFFF):
                    continue
                enc_key = scanner.read_pointer(ptr, KEY_SIZE)
                if enc_key is None:
                    continue
                if enc_key in seen or enc_key == b"\x00" * KEY_SIZE or len(set(enc_key)) < 12:
                    continue
                seen.add(enc_key)

                for rel in list(remaining):
                    if _verify_enc_key_for_db(enc_key, dbs[rel]):
                        found[rel] = enc_key.hex()
                        remaining.discard(rel)
                        logger.info("Found key for %s", rel)
                        if progress_fn:
                            progress_fn(
                                f"Found key for {rel} ({len(found)}/{len(dbs)})"
                            )
                tested += 1

                if progress_fn and tested % 10000 == 0 and tested > 0:
                    elapsed = time.time() - t_start
                    progress_fn(
                        f"Scanned {tested} candidates ({tested/elapsed:.0f}/s), "
                        f"{len(found)}/{len(dbs)} keys found..."
                    )

        elapsed = time.time() - t_start
        logger.info(
            "Scan complete: %d candidates in %.1fs, found %d/%d keys",
            tested, elapsed, len(found), len(dbs),
        )

    finally:
        scanner.close()

    if not found:
        raise RuntimeError(
            "No valid keys found in WeChat process memory. "
            "Ensure WeChat is running and logged in."
        )

    return found


def extract_key(
    pid: Optional[int] = None,
    validate_fn: Optional[Callable[[str], bool]] = None,
    db_dir: Optional[str] = None,
) -> str:
    """Legacy single-key extraction interface.

    Returns a JSON-encoded dict of {db_rel_path: derived_key_hex}.
    """
    if db_dir is None:
        # Try to auto-discover
        from wxtools.plugins.wechat.account_discovery import (
            discover_accounts,
            find_wechat_data_dir,
        )

        data_dir = find_wechat_data_dir()
        if data_dir:
            accounts = discover_accounts(data_dir)
            if accounts:
                db_dir = accounts[0]["db_dir"]

    if not db_dir:
        raise RuntimeError("Cannot find WeChat database directory")

    keys = extract_keys(db_dir, pid=pid)
    return json.dumps(keys)
