"""Discover WeChat accounts on this machine."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Union

WXID_PATTERN = re.compile(r"^wxid_[a-zA-Z0-9]+$")


def find_wechat_data_dir(documents_dir: Optional[Path] = None) -> Optional[Path]:
    """Auto-discover WeChat data root. Checks 4.x path first, then 3.x."""
    if documents_dir is None:
        documents_dir = Path.home() / "Documents"
    xwechat = documents_dir / "xwechat_files"
    if xwechat.is_dir():
        return xwechat
    wechat3 = documents_dir / "WeChat Files"
    if wechat3.is_dir():
        return wechat3
    return None


def discover_accounts(data_dir: Union[str, Path]) -> List[Dict[str, str]]:
    """List all wxid accounts found under data_dir."""
    data_path = Path(data_dir)
    if not data_path.is_dir():
        return []
    accounts = []
    for child in sorted(data_path.iterdir()):
        if child.is_dir() and WXID_PATTERN.match(child.name):
            db_storage = child / "db_storage"
            if not db_storage.is_dir():
                db_storage = child / "Msg"  # 3.x layout
            if db_storage.is_dir():
                accounts.append({
                    "wxid": child.name,
                    "path": str(child),
                    "db_dir": str(db_storage),
                })
    return accounts
