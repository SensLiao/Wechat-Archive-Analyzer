"""Key management application service.

Extracts key lifecycle business logic from the CLI layer into a
framework-agnostic service.  No Click dependency, no interactive prompts.
All parameters are accepted explicitly; errors are raised as WxToolsError
subclasses.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from wxtools.domain.errors import (
    AccountNotFoundError,
    DbNotFoundError,
    KeyNotFoundError,
    KeyPasswordWrongError,
    PlatformNotSupportedError,
    WxToolsError,
)
from wxtools.infrastructure.secrets.keystore import Keystore
from wxtools.infrastructure.secrets.unlock_session import UnlockSession

if TYPE_CHECKING:
    from wxtools.runtime.config import Config

logger = logging.getLogger("wxtools.application.key")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_account(cfg: Config, wxid: str | None) -> str | None:
    """Resolve wxid from explicit arg, config, or auto-discovery."""
    if wxid:
        return wxid
    active = cfg.get("active_account", "auto")
    if active != "auto":
        return active
    from wxtools.infrastructure.wechat.account_discovery import (
        discover_accounts,
        find_wechat_data_dir,
    )

    data_dir = cfg.get("wechat_data_dir", "auto")
    if data_dir == "auto":
        data_dir = find_wechat_data_dir()
    if not data_dir:
        return None
    accounts = discover_accounts(data_dir)
    if len(accounts) == 1:
        return accounts[0]["wxid"]
    return None


def _find_db_dir(cfg: Config, wxid: str) -> Path | None:
    """Resolve the db_storage directory for a given wxid."""
    from wxtools.infrastructure.wechat.account_discovery import (
        discover_accounts,
        find_wechat_data_dir,
    )

    data_dir = cfg.get("wechat_data_dir", "auto")
    if data_dir == "auto":
        data_dir = find_wechat_data_dir()
    if not data_dir:
        return None
    accounts = discover_accounts(data_dir)
    for acc in accounts:
        if acc["wxid"] == wxid:
            return Path(acc["db_dir"])
    # Fallback: direct path
    if data_dir:
        candidate = Path(data_dir) / wxid / "db_storage"
        if candidate.is_dir():
            return candidate
    return None


def _determine_protection(
    cfg: Config,
    ks: Keystore,
    wxid: str,
    password: str | None,
    no_password: bool,
) -> str:
    """Decide which keystore backend to use (non-interactive)."""
    config_protection = cfg.get("keystore_protection", "auto")
    if config_protection != "auto":
        return config_protection
    if password:
        return "password-file"
    if no_password:
        return "auto"
    return "auto"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_status(cfg: Config) -> list[dict[str, Any]]:
    """List stored keys metadata (sensitive data masked)."""
    ks = Keystore(cfg.keys_dir)
    keys = ks.list_keys()
    return [
        {
            "wxid": k.get("wxid", ""),
            "plugin": k.get("plugin", ""),
            "protection": k.get("protection", ""),
            "created_at": k.get("created_at", ""),
            "last_verified": k.get("last_verified", ""),
        }
        for k in keys
    ]


def extract_key(
    cfg: Config,
    wxid: str | None = None,
    password: str | None = None,
    no_password: bool = False,
    progress_fn: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Extract encryption keys from a running WeChat process.

    Returns:
        Dict with ``account``, ``protection``, ``status``, and ``db_count``.

    Raises:
        PlatformNotSupportedError: On unsupported platforms.
        WxToolsError: On extraction or storage failure.
    """
    if sys.platform not in ("win32", "darwin"):
        raise PlatformNotSupportedError("key extraction", sys.platform)

    from wxtools.infrastructure.wechat.account_discovery import (
        discover_accounts,
        find_wechat_data_dir,
    )
    from wxtools.infrastructure.wechat.key_extractor import extract_keys

    resolved_wxid = _resolve_account(cfg, wxid)
    data_dir = cfg.get("wechat_data_dir", "auto")
    if data_dir == "auto":
        data_dir = find_wechat_data_dir()

    db_dir: str | None = None
    if data_dir:
        accounts = discover_accounts(data_dir)
        for acc in accounts:
            if not resolved_wxid or acc["wxid"] == resolved_wxid:
                resolved_wxid = acc["wxid"]
                db_dir = acc["db_dir"]
                break

    if not resolved_wxid:
        resolved_wxid = "unknown"
    if not db_dir:
        raise DbNotFoundError("Cannot find WeChat database directory")

    keys = extract_keys(db_dir, progress_fn=progress_fn)
    key_data = json.dumps(keys)

    ks = Keystore(cfg.keys_dir)
    protection = _determine_protection(cfg, ks, resolved_wxid, password, no_password)

    ks.store_key(
        "wechat",
        resolved_wxid,
        key_data.encode("ascii"),
        backend_name=protection,
        password=password,
    )

    return {
        "account": resolved_wxid,
        "protection": protection,
        "status": "stored",
        "db_count": len(keys),
    }


def verify_key(
    cfg: Config,
    wxid: str,
    password: str | None = None,
) -> dict[str, Any]:
    """Verify a stored key against encrypted databases.

    Returns:
        Dict with ``account``, ``total``, ``passed``, ``failed``, ``details``.

    Raises:
        AccountNotFoundError: When wxid cannot be resolved.
        KeyNotFoundError: When no key is stored for the account.
        KeyPasswordWrongError: When password is wrong.
        DbNotFoundError: When database directory is not found.
    """
    from wxtools.infrastructure.wechat.key_validator import validate_key_for_account

    ks = Keystore(cfg.keys_dir)
    raw_key = ks.get_key("wechat", wxid, password=password)
    key_data = raw_key.decode("ascii")

    # Find DB directory
    db_dir_str = cfg.get("wechat_db_dir", None)
    if db_dir_str and db_dir_str != "auto":
        db_dir = Path(db_dir_str)
    else:
        db_dir = _find_db_dir(cfg, wxid)

    if not db_dir or not db_dir.is_dir():
        raise DbNotFoundError("Database directory not found for verification")

    result = validate_key_for_account(key_data, db_dir)

    # Update last_verified timestamp
    now = datetime.now(timezone.utc).isoformat()
    ks.update_metadata("wechat", wxid, {"last_verified": now})

    return {"account": wxid, **result}


def set_key(
    cfg: Config,
    wxid: str,
    key_input: str,
    password: str | None = None,
    no_password: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Manually set a decryption key (64-char hex or JSON file path).

    Returns:
        Dict with ``account``, ``protection``, ``status``, and optional
        ``validation`` result.

    Raises:
        AccountNotFoundError: When wxid is not provided.
        WxToolsError: On invalid key format or storage failure.
    """
    from wxtools.infrastructure.wechat.key_validator import validate_key_for_account

    # Parse key_input: file path or 64-char hex
    key_path = Path(key_input)
    if key_path.is_file():
        try:
            key_data = key_path.read_text(encoding="utf-8").strip()
            json.loads(key_data)  # validate JSON
        except (json.JSONDecodeError, OSError) as exc:
            raise WxToolsError(
                "INVALID_KEY_FORMAT",
                f"Cannot read key file: {exc}",
                "Provide a valid JSON key file.",
            ) from exc
    elif re.match(r"^[0-9a-fA-F]{64}$", key_input):
        key_data = key_input
    else:
        raise WxToolsError(
            "INVALID_KEY_FORMAT",
            "Key must be a 64-char hex string or a valid JSON file path.",
            "Provide a 64-char hex string or JSON file.",
        )

    # Validate against DB if possible
    validation: dict[str, Any] | None = None
    db_dir_str = cfg.get("wechat_db_dir", None)
    if db_dir_str and db_dir_str != "auto":
        db_dir: Path | None = Path(db_dir_str)
    else:
        db_dir = _find_db_dir(cfg, wxid)

    if db_dir and db_dir.is_dir():
        validation = validate_key_for_account(key_data, db_dir)
        if validation["failed"] > 0 and not force:
            raise WxToolsError(
                "KEY_VALIDATION_PARTIAL",
                f"Verification partially failed ({validation['passed']}/{validation['total']} passed).",
                "Use force=True to save anyway.",
            )

    # Store
    ks = Keystore(cfg.keys_dir)
    protection = _determine_protection(cfg, ks, wxid, password, no_password)

    ks.store_key(
        "wechat",
        wxid,
        key_data.encode("ascii"),
        backend_name=protection,
        password=password,
    )

    result: dict[str, Any] = {
        "account": wxid,
        "protection": protection,
        "status": "stored",
    }
    if validation is not None:
        result["validation"] = validation
    return result


def unlock(
    cfg: Config,
    wxid: str,
    password: str | None = None,
    ttl: int | None = None,
) -> dict[str, Any]:
    """Create an unlock session for the given account.

    Returns:
        Dict with ``account``, ``status``, ``ttl_minutes``.

    Raises:
        KeyNotFoundError: When no key is stored.
        KeyPasswordWrongError: When password is wrong.
    """
    ks = Keystore(cfg.keys_dir)
    session = UnlockSession(cfg.session_dir)

    if not ks.has_key("wechat", wxid):
        raise KeyNotFoundError(wxid)

    # Already unlocked?
    existing = session.get_key("wechat", wxid)
    if existing is not None:
        return {"account": wxid, "status": "already_unlocked"}

    # Retrieve key
    try:
        raw_key = ks.get_key("wechat", wxid, password=password)
    except KeyPasswordWrongError:
        # Try environment variable as fallback
        env_pw = os.environ.get("WXTOOLS_PASSWORD")
        if env_pw:
            raw_key = ks.get_key("wechat", wxid, password=env_pw)
        else:
            raise

    # Determine TTL from metadata or param
    ttl_minutes = ttl if ttl is not None else 120
    if ttl is None:
        meta_path = ks._meta_path("wechat", wxid)
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text("utf-8"))
                ttl_minutes = meta.get("session_ttl_minutes", 120)
            except (json.JSONDecodeError, OSError):
                pass

    session.create("wechat", wxid, raw_key, ttl_minutes=ttl_minutes, password=password)

    return {"account": wxid, "status": "unlocked", "ttl_minutes": ttl_minutes}


def lock(
    cfg: Config,
    wxid: str | None = None,
    clear_all: bool = False,
) -> dict[str, Any]:
    """Clear unlock session(s).

    Returns:
        Dict with ``status`` and optionally ``account``.

    Raises:
        AccountNotFoundError: When wxid cannot be resolved and clear_all is False.
    """
    session = UnlockSession(cfg.session_dir)

    if clear_all:
        session.clear_all()
        return {"status": "all_sessions_cleared"}

    resolved = _resolve_account(cfg, wxid)
    if not resolved:
        raise AccountNotFoundError("")

    session.clear("wechat", resolved)
    return {"account": resolved, "status": "locked"}
