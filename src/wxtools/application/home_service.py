"""Home / workbench summary service.

Aggregates high-level status data for the GUI home page by combining
account discovery, keystore, and cache information.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from wxtools.application.account_service import list_accounts
from wxtools.application.cache_service import get_status as get_cache_status
from wxtools.application.key_service import get_status as get_key_status
from wxtools.core.keystore import Keystore

if TYPE_CHECKING:
    from wxtools.core.config import Config

logger = logging.getLogger("wxtools.application.home")


def get_summary(cfg: Config) -> dict[str, Any]:
    """Return an aggregated summary for the workbench home page.

    Returns a dict with:
        - ``accounts``: discovered accounts and active account info
        - ``keys``: stored key metadata
        - ``cache``: cache directory stats
        - ``recent_searches``: placeholder (empty list for v5)
        - ``recent_exports``: placeholder (empty list for v5)
        - ``recent_workspaces``: placeholder (empty list for v5)
    """
    # --- Account status ---
    accounts = list_accounts(cfg)
    active_account = cfg.get("active_account", "auto")
    if active_account == "auto" and len(accounts) == 1:
        active_account = accounts[0]["wxid"]

    account_summary = {
        "discovered": [a["wxid"] for a in accounts],
        "count": len(accounts),
        "active": active_account if active_account != "auto" else None,
    }

    # --- Key status ---
    stored_keys = get_key_status(cfg)
    ks = Keystore(cfg.keys_dir)
    verified_wxids = [
        k["wxid"] for k in stored_keys if k.get("last_verified")
    ]

    key_summary = {
        "stored": len(stored_keys),
        "verified": len(verified_wxids),
        "accounts": [k["wxid"] for k in stored_keys],
    }

    # --- Cache status ---
    cache_info = get_cache_status(cfg)
    cache_summary = {
        "exists": cache_info["total_size_bytes"] > 0,
        "size_bytes": cache_info["total_size_bytes"],
        "size_human": cache_info["total_size_human"],
        "account_count": len(cache_info["accounts"]),
    }

    return {
        "accounts": account_summary,
        "keys": key_summary,
        "cache": cache_summary,
        "recent_searches": [],
        "recent_exports": [],
        "recent_workspaces": [],
    }
