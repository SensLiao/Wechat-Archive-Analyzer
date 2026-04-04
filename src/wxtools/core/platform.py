"""Platform detection and default backend selection."""
from __future__ import annotations

import sys

_PLATFORM_MAP = {
    "win32": "windows",
    "darwin": "macos",
    "linux": "linux",
}

_DEFAULT_BACKENDS = {
    "windows": "windows-dpapi",
    "macos": "macos-keychain",
    "linux": "linux-secret-service",
}


def current_platform() -> str:
    """Return normalized platform name: 'windows', 'macos', or 'linux'."""
    return _PLATFORM_MAP.get(sys.platform, "linux")


def get_default_backend_name() -> str:
    """Return the preferred secret backend name for the current platform."""
    return _DEFAULT_BACKENDS[current_platform()]
