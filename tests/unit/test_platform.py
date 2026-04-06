"""Tests for platform detection and default backend selection."""
import sys
from unittest.mock import patch

from wxtools.runtime.platform import current_platform, get_default_backend_name


def test_current_platform_returns_known_value():
    plat = current_platform()
    assert plat in ("windows", "macos", "linux")


def test_windows_default_backend():
    with patch.object(sys, "platform", "win32"):
        assert get_default_backend_name() == "windows-dpapi"


def test_macos_default_backend():
    with patch.object(sys, "platform", "darwin"):
        assert get_default_backend_name() == "macos-keychain"


def test_linux_default_backend():
    with patch.object(sys, "platform", "linux"):
        assert get_default_backend_name() == "linux-secret-service"
