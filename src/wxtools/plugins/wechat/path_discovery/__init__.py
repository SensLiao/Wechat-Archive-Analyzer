"""Platform-dispatched WeChat data directory discovery."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from wxtools.plugins.wechat.path_discovery.linux import LinuxPathDiscoverer
from wxtools.plugins.wechat.path_discovery.macos import MacosPathDiscoverer
from wxtools.plugins.wechat.path_discovery.windows import WindowsPathDiscoverer

_DISCOVERERS = {
    "win32": WindowsPathDiscoverer,
    "darwin": MacosPathDiscoverer,
    "linux": LinuxPathDiscoverer,
}


def discover_data_dir(home_dir: Optional[Path] = None) -> Optional[Path]:
    """Discover WeChat data directory for the current platform."""
    cls = _DISCOVERERS.get(sys.platform, LinuxPathDiscoverer)
    return cls().discover(home_dir=home_dir)
