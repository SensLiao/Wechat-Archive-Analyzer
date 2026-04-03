"""WeChat data source plugin."""

from __future__ import annotations

from typing import Any, Dict, List

from wxtools.core.base_plugin import BasePlugin


class WeChatPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "wechat"

    def setup(self, config: Dict[str, Any]) -> None:
        self._config = config

    def get_accounts(self) -> List[Dict[str, str]]:
        from wxtools.plugins.wechat.account_discovery import discover_accounts
        data_dir = self._config.get("wechat_data_dir", "auto")
        return discover_accounts(data_dir)

    def get_reader(self, account_id: str) -> Any:
        from wxtools.plugins.wechat.db_reader import DbReader
        cache_dir = self._config.get("cache_dir", "")
        return DbReader(account_id, cache_dir)
