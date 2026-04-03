from wxtools.core.base_plugin import BasePlugin
from wxtools.core.plugin_registry import get_plugin, list_plugins


def test_list_plugins_includes_wechat():
    plugins = list_plugins()
    assert "wechat" in plugins


def test_get_wechat_plugin():
    plugin = get_plugin("wechat")
    assert isinstance(plugin, BasePlugin)
    assert plugin.name == "wechat"


def test_get_nonexistent_plugin_raises():
    import pytest
    with pytest.raises(KeyError):
        get_plugin("nonexistent")
