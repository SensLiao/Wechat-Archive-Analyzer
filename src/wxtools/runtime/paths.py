"""Centralized path resolution for CLI and Desktop modes."""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional


class RuntimeMode(Enum):
    CLI = "cli"  # Uses ~/.wxtools/
    DESKTOP = "desktop"  # Uses platform-specific app data directory
    DEV = "dev"  # Uses project-local or provided home


def _platform_app_data_dir() -> Path:
    """Return the platform-specific application data directory for wxtools.

    Windows:  %LOCALAPPDATA%/wxtools
    macOS:    ~/Library/Application Support/wxtools
    Linux:    $XDG_DATA_HOME/wxtools  (default ~/.local/share/wxtools)
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "wxtools"
        return Path.home() / "AppData" / "Local" / "wxtools"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "wxtools"
    # Linux / other Unix
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "wxtools"
    return Path.home() / ".local" / "share" / "wxtools"


class AppPaths:
    """Resolved application paths based on runtime mode."""

    def __init__(
        self,
        mode: RuntimeMode = RuntimeMode.CLI,
        home: Optional[Path] = None,
    ) -> None:
        self._mode = mode
        if home is not None:
            self._home = Path(home)
        elif mode == RuntimeMode.CLI:
            self._home = Path.home() / ".wxtools"
        elif mode == RuntimeMode.DESKTOP:
            self._home = _platform_app_data_dir()
        else:
            # DEV mode without explicit home: use cwd-local .wxtools
            self._home = Path.cwd() / ".wxtools"

    @property
    def mode(self) -> RuntimeMode:
        return self._mode

    @property
    def home_dir(self) -> Path:
        return self._home

    @property
    def cache_dir(self) -> Path:
        return self._home / "cache"

    @property
    def keys_dir(self) -> Path:
        return self._home / "keys"

    @property
    def logs_dir(self) -> Path:
        return self._home / "logs"

    @property
    def session_dir(self) -> Path:
        return self._home / "session"

    @property
    def workspaces_dir(self) -> Path:
        return self._home / "workspaces"

    @property
    def exports_dir(self) -> Path:
        return self._home / "exports"
