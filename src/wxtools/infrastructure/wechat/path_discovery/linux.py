"""Linux-specific WeChat data directory discovery."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class LinuxPathDiscoverer:
    """Discover WeChat data directory on Linux."""

    def discover(self, home_dir: Optional[Path] = None) -> Optional[Path]:
        if home_dir is None:
            home_dir = Path.home()
        xdg = os.environ.get("XDG_DATA_HOME", str(home_dir / ".local" / "share"))
        wechat_dir = Path(xdg) / "wechat"
        if wechat_dir.is_dir():
            return wechat_dir
        # Wine installation fallback
        wine_dir = (
            home_dir
            / ".wine"
            / "drive_c"
            / "Users"
            / "user"
            / "Documents"
            / "xwechat_files"
        )
        if wine_dir.is_dir():
            return wine_dir
        return None
