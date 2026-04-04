"""Windows-specific WeChat data directory discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class WindowsPathDiscoverer:
    """Discover WeChat data directory on Windows."""

    def discover(self, home_dir: Optional[Path] = None) -> Optional[Path]:
        if home_dir is None:
            home_dir = Path.home()
        # WeChat 4.x: directly under user home
        xwechat = home_dir / "xwechat_files"
        if xwechat.is_dir():
            return xwechat
        # WeChat 4.x: under Documents
        docs_xwechat = home_dir / "Documents" / "xwechat_files"
        if docs_xwechat.is_dir():
            return docs_xwechat
        # WeChat 3.x fallback
        wechat3 = home_dir / "Documents" / "WeChat Files"
        if wechat3.is_dir():
            return wechat3
        return None
