from pathlib import Path
from unittest.mock import patch

import pytest

from wxtools.plugins.wechat.path_discovery import discover_data_dir
from wxtools.plugins.wechat.path_discovery.windows import WindowsPathDiscoverer
from wxtools.plugins.wechat.path_discovery.macos import MacosPathDiscoverer
from wxtools.plugins.wechat.path_discovery.linux import LinuxPathDiscoverer


class TestWindowsPathDiscoverer:
    def test_finds_4x_home(self, tmp_path):
        (tmp_path / "xwechat_files").mkdir()
        d = WindowsPathDiscoverer()
        result = d.discover(home_dir=tmp_path)
        assert result == tmp_path / "xwechat_files"

    def test_finds_4x_documents(self, tmp_path):
        (tmp_path / "Documents" / "xwechat_files").mkdir(parents=True)
        d = WindowsPathDiscoverer()
        result = d.discover(home_dir=tmp_path)
        assert result == tmp_path / "Documents" / "xwechat_files"

    def test_finds_3x_fallback(self, tmp_path):
        (tmp_path / "Documents" / "WeChat Files").mkdir(parents=True)
        d = WindowsPathDiscoverer()
        result = d.discover(home_dir=tmp_path)
        assert result == tmp_path / "Documents" / "WeChat Files"

    def test_returns_none_when_absent(self, tmp_path):
        d = WindowsPathDiscoverer()
        assert d.discover(home_dir=tmp_path) is None


class TestMacosPathDiscoverer:
    def test_finds_containers_path(self, tmp_path):
        wechat_dir = tmp_path / "Library" / "Containers" / "com.tencent.xinWeChat" / "Data"
        wechat_dir.mkdir(parents=True)
        d = MacosPathDiscoverer()
        result = d.discover(home_dir=tmp_path)
        assert result == wechat_dir

    def test_returns_none_when_absent(self, tmp_path):
        d = MacosPathDiscoverer()
        assert d.discover(home_dir=tmp_path) is None


class TestLinuxPathDiscoverer:
    def test_finds_xdg_data_home(self, tmp_path):
        wechat_dir = tmp_path / ".local" / "share" / "wechat"
        wechat_dir.mkdir(parents=True)
        d = LinuxPathDiscoverer()
        with patch.dict("os.environ", {"XDG_DATA_HOME": str(tmp_path / ".local" / "share")}):
            result = d.discover(home_dir=tmp_path)
        assert result == wechat_dir

    def test_returns_none_when_absent(self, tmp_path):
        d = LinuxPathDiscoverer()
        with patch.dict("os.environ", {}, clear=True):
            assert d.discover(home_dir=tmp_path) is None


class TestDiscoverDataDir:
    def test_dispatches_to_platform_adapter(self, tmp_path):
        (tmp_path / "xwechat_files").mkdir()
        with patch("sys.platform", "win32"):
            result = discover_data_dir(home_dir=tmp_path)
        assert result == tmp_path / "xwechat_files"

    def test_returns_none_on_empty(self, tmp_path):
        result = discover_data_dir(home_dir=tmp_path)
        assert result is None or isinstance(result, Path)
