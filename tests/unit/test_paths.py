"""Tests for wxtools.runtime.paths — AppPaths resolution in all modes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from wxtools.runtime.paths import AppPaths, RuntimeMode, _platform_app_data_dir


class TestAppPathsCLI:
    """CLI mode uses ~/.wxtools/."""

    def test_default_home(self):
        paths = AppPaths(mode=RuntimeMode.CLI)
        assert paths.home_dir == Path.home() / ".wxtools"

    def test_subdirectories(self):
        paths = AppPaths(mode=RuntimeMode.CLI)
        home = Path.home() / ".wxtools"
        assert paths.cache_dir == home / "cache"
        assert paths.keys_dir == home / "keys"
        assert paths.logs_dir == home / "logs"
        assert paths.session_dir == home / "session"
        assert paths.workspaces_dir == home / "workspaces"
        assert paths.exports_dir == home / "exports"

    def test_mode_property(self):
        paths = AppPaths(mode=RuntimeMode.CLI)
        assert paths.mode == RuntimeMode.CLI


class TestAppPathsDesktop:
    """Desktop mode uses platform-specific app data directory."""

    def test_desktop_home_uses_platform_dir(self):
        paths = AppPaths(mode=RuntimeMode.DESKTOP)
        expected = _platform_app_data_dir()
        assert paths.home_dir == expected

    def test_desktop_subdirectories(self):
        paths = AppPaths(mode=RuntimeMode.DESKTOP)
        home = paths.home_dir
        assert paths.cache_dir == home / "cache"
        assert paths.keys_dir == home / "keys"
        assert paths.logs_dir == home / "logs"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_windows_desktop_uses_localappdata(self, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", "C:\\Users\\Test\\AppData\\Local")
        result = _platform_app_data_dir()
        assert result == Path("C:/Users/Test/AppData/Local/wxtools")

    def test_mode_property(self):
        paths = AppPaths(mode=RuntimeMode.DESKTOP)
        assert paths.mode == RuntimeMode.DESKTOP


class TestAppPathsDev:
    """DEV mode uses provided home or cwd-local .wxtools/."""

    def test_dev_with_explicit_home(self, tmp_path):
        custom = tmp_path / "my_project" / ".wxtools"
        paths = AppPaths(mode=RuntimeMode.DEV, home=custom)
        assert paths.home_dir == custom
        assert paths.cache_dir == custom / "cache"
        assert paths.keys_dir == custom / "keys"

    def test_dev_without_home_uses_cwd(self):
        paths = AppPaths(mode=RuntimeMode.DEV)
        assert paths.home_dir == Path.cwd() / ".wxtools"

    def test_mode_property(self):
        paths = AppPaths(mode=RuntimeMode.DEV)
        assert paths.mode == RuntimeMode.DEV


class TestAppPathsHomeOverride:
    """Explicit home overrides all modes."""

    def test_cli_with_custom_home(self, tmp_path):
        custom = tmp_path / "custom"
        paths = AppPaths(mode=RuntimeMode.CLI, home=custom)
        assert paths.home_dir == custom
        assert paths.logs_dir == custom / "logs"

    def test_desktop_with_custom_home(self, tmp_path):
        custom = tmp_path / "custom_desktop"
        paths = AppPaths(mode=RuntimeMode.DESKTOP, home=custom)
        assert paths.home_dir == custom

    def test_all_subdirs_relative_to_home(self, tmp_path):
        paths = AppPaths(mode=RuntimeMode.CLI, home=tmp_path)
        assert paths.cache_dir == tmp_path / "cache"
        assert paths.keys_dir == tmp_path / "keys"
        assert paths.logs_dir == tmp_path / "logs"
        assert paths.session_dir == tmp_path / "session"
        assert paths.workspaces_dir == tmp_path / "workspaces"
        assert paths.exports_dir == tmp_path / "exports"


class TestRuntimeModeEnum:
    """RuntimeMode enum values."""

    def test_values(self):
        assert RuntimeMode.CLI.value == "cli"
        assert RuntimeMode.DESKTOP.value == "desktop"
        assert RuntimeMode.DEV.value == "dev"

    def test_from_string(self):
        assert RuntimeMode("cli") == RuntimeMode.CLI
        assert RuntimeMode("desktop") == RuntimeMode.DESKTOP
        assert RuntimeMode("dev") == RuntimeMode.DEV
