"""Base protocol for platform-specific path discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol


class PathDiscoverer(Protocol):
    """Protocol for platform-specific WeChat data directory discovery."""

    def discover(self, home_dir: Optional[Path] = None) -> Optional[Path]: ...
