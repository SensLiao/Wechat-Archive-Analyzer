"""Platform-dispatched memory scanner."""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wxtools.plugins.wechat.memory_scanner.base import MemoryScanner


def get_scanner() -> MemoryScanner:
    """Return a MemoryScanner for the current platform."""
    if sys.platform == "win32":
        from wxtools.plugins.wechat.memory_scanner.windows import WindowsMemoryScanner
        return WindowsMemoryScanner()
    elif sys.platform == "darwin":
        from wxtools.plugins.wechat.memory_scanner.macos import MacosMemoryScanner
        return MacosMemoryScanner()
    else:
        raise OSError(
            "Key extraction requires reading WeChat process memory.\n"
            "Supported platforms: Windows, macOS.\n"
            "On Linux, use 'wxtools key set <hex-or-json>' to import a known key."
        )
