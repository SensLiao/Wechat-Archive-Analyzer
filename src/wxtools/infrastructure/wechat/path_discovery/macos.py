"""macOS-specific WeChat data directory discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class MacosPathDiscoverer:
    """Discover WeChat data directory on macOS."""

    def discover(self, home_dir: Optional[Path] = None) -> Optional[Path]:
        if home_dir is None:
            home_dir = Path.home()
        container = (
            home_dir / "Library" / "Containers" / "com.tencent.xinWeChat" / "Data"
        )
        if container.is_dir():
            return container
        return None
