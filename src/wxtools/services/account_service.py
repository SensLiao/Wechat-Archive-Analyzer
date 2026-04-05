"""Account resolution and key retrieval service.

Extracts shared business logic from CLI commands (key.py, query.py) into a
framework-agnostic service layer.  No Click dependency, no interactive prompts,
no printing — callers receive structured return values or raised exceptions.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from wxtools.core.errors import (
    AccountNotFoundError,
    DbNotFoundError,
    KeyNotFoundError,
    KeyPasswordWrongError,
)
from wxtools.core.keystore import Keystore
from wxtools.core.unlock_session import UnlockSession

if TYPE_CHECKING:
    from wxtools.core.config import Config
    from wxtools.plugins.wechat.db_reader import DbReader

logger = logging.getLogger("wxtools.services.account")


# ---------------------------------------------------------------------------
# Data directory
# ---------------------------------------------------------------------------

def resolve_data_dir(cfg: Config) -> Path:
    """Return the WeChat data directory, auto-detecting if configured as ``"auto"``.

    Raises:
        DbNotFoundError: When auto-detection fails and no explicit path is set.
    """
    from wxtools.plugins.wechat.account_discovery import find_wechat_data_dir

    data_dir = cfg.get("wechat_data_dir", "auto")
    if data_dir == "auto":
        data_dir = find_wechat_data_dir()
    if not data_dir:
        raise DbNotFoundError("auto-detect failed")
    return Path(data_dir)


# ---------------------------------------------------------------------------
# Account listing / resolution
# ---------------------------------------------------------------------------

def list_accounts(cfg: Config) -> list[dict]:
    """Discover all WeChat accounts under the data directory.

    Returns an empty list when the data directory cannot be resolved.
    Each dict contains at least ``wxid``, ``db_dir``, and ``path`` keys.
    """
    from wxtools.plugins.wechat.account_discovery import discover_accounts

    try:
        data_dir = resolve_data_dir(cfg)
    except DbNotFoundError:
        return []
    return discover_accounts(data_dir)


def resolve_wxid(cfg: Config, account_arg: str | None) -> str:
    """Determine the effective wxid from an explicit argument, config, or auto-discovery.

    Resolution order:
        1. *account_arg* if provided.
        2. ``active_account`` config value (when not ``"auto"``).
        3. First account returned by auto-discovery.

    Raises:
        AccountNotFoundError: When no account can be determined.
    """
    if account_arg:
        return account_arg

    active = cfg.get("active_account", "auto")
    if active != "auto":
        return active

    accounts = list_accounts(cfg)
    if not accounts:
        raise AccountNotFoundError("")
    return accounts[0]["wxid"]


# ---------------------------------------------------------------------------
# Key retrieval
# ---------------------------------------------------------------------------

def get_key(
    cfg: Config,
    wxid: str,
    password: str | None = None,
) -> bytes:
    """Retrieve the decryption key for *wxid* without interactive prompts.

    Attempt order:
        1. Active unlock session (already cached in memory).
        2. Explicit *password* parameter.
        3. DPAPI / system backend (no password).
        4. ``WXTOOLS_PASSWORD`` environment variable.

    Raises:
        KeyNotFoundError: When all retrieval strategies are exhausted.
    """
    ks = Keystore(cfg.keys_dir)
    session = UnlockSession(cfg.session_dir)

    # 1. Session cache
    session_key = session.get_key("wechat", wxid)
    if session_key is not None:
        return session_key

    # 2. Explicit password
    if password:
        return ks.get_key("wechat", wxid, password=password)

    # 3. System backend (DPAPI / Keychain)
    try:
        return ks.get_key("wechat", wxid)
    except KeyPasswordWrongError:
        pass

    # 4. Environment variable
    env_password = os.environ.get("WXTOOLS_PASSWORD")
    if env_password:
        try:
            return ks.get_key("wechat", wxid, password=env_password)
        except KeyPasswordWrongError:
            pass

    raise KeyNotFoundError(wxid)


# ---------------------------------------------------------------------------
# Full account + DbReader resolution
# ---------------------------------------------------------------------------

def resolve_account_and_reader(
    cfg: Config,
    account_arg: str | None = None,
    password: str | None = None,
) -> tuple[DbReader, Path]:
    """Resolve account, decrypt databases if needed, and return a ready reader.

    This is the high-level entry point that most callers need.  It combines
    :func:`resolve_wxid`, :func:`get_key`, and decryption into a single call.

    Returns:
        A 2-tuple of ``(DbReader, account_data_path)`` where
        *account_data_path* is the on-disk account root (useful for
        attachment resolution).

    Raises:
        AccountNotFoundError: When the wxid cannot be matched to a local account.
        DbNotFoundError: When the data directory cannot be located.
        KeyNotFoundError: When no usable key is available.
    """
    from wxtools.plugins.wechat.account_discovery import discover_accounts
    from wxtools.plugins.wechat.db_reader import DbReader
    from wxtools.plugins.wechat.decryptor import Decryptor

    data_dir = resolve_data_dir(cfg)
    wxid = resolve_wxid(cfg, account_arg)

    # Match wxid to a discovered account entry
    accounts = discover_accounts(data_dir)
    db_dir: str | None = None
    account_path: str | None = None
    for acc in accounts:
        if acc["wxid"] == wxid:
            db_dir = acc["db_dir"]
            account_path = acc["path"]
            break

    if not db_dir:
        raise AccountNotFoundError(wxid)

    # Decrypt (incremental — only re-decrypts when source is newer than cache)
    cache_dir = cfg.cache_dir
    account_cache = cache_dir / wxid

    raw_key = get_key(cfg, wxid, password=password)
    key_data = raw_key.decode("ascii")

    decryptor = Decryptor()
    decryptor.decrypt_all(Path(db_dir), account_cache, key_data)

    return DbReader(wxid, cache_dir), Path(account_path)
