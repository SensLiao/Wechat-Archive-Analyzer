"""Abstract base plugin interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BasePlugin(ABC):
    """Thin abstract shell for data source plugins."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def setup(self, config: Dict[str, Any]) -> None: ...

    @abstractmethod
    def get_accounts(self) -> List[Dict[str, str]]: ...

    @abstractmethod
    def get_reader(self, account_id: str) -> Any: ...
