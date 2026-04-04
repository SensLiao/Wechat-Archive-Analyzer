"""Discover WeChat accounts on this machine."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Union

# WeChat 4.x uses wxid_<alphanum>_<digits> folder names
WXID_DIR_PATTERN = re.compile(r"^wxid_[a-zA-Z0-9]+(_\d+)?$")
# WeChat 3.x uses plain wxid_<alphanum>
WXID_PATTERN = re.compile(r"^wxid_[a-zA-Z0-9]+$")


def find_wechat_data_dir(home_dir: Optional[Path] = None) -> Optional[Path]:
    """Auto-discover WeChat data root. Delegates to platform-specific adapter."""
    from wxtools.plugins.wechat.path_discovery import discover_data_dir

    return discover_data_dir(home_dir=home_dir)


def _extract_wxid(dirname: str) -> Optional[str]:
    """Extract base wxid from directory name (strips _NNNN suffix for 4.x)."""
    m = WXID_DIR_PATTERN.match(dirname)
    if m:
        # Return just the wxid part (before the _NNNN suffix)
        if m.group(1):
            return dirname[: -len(m.group(1))]
        return dirname
    if WXID_PATTERN.match(dirname):
        return dirname
    return None


def discover_accounts(data_dir: Union[str, Path]) -> List[Dict[str, str]]:
    """List all wxid accounts found under data_dir."""
    data_path = Path(data_dir)
    if not data_path.is_dir():
        return []
    accounts = []
    for child in sorted(data_path.iterdir()):
        if not child.is_dir():
            continue
        wxid = _extract_wxid(child.name)
        if not wxid:
            continue
        # WeChat 4.x: db_storage subfolder
        db_storage = child / "db_storage"
        if db_storage.is_dir():
            accounts.append({
                "wxid": wxid,
                "path": str(child),
                "db_dir": str(db_storage),
                "version": "4.x",
            })
            continue
        # WeChat 3.x: Msg subfolder
        msg_dir = child / "Msg"
        if msg_dir.is_dir():
            accounts.append({
                "wxid": wxid,
                "path": str(child),
                "db_dir": str(msg_dir),
                "version": "3.x",
            })
    return accounts
