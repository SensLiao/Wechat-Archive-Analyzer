"""Plugin discovery via entry_points."""

from __future__ import annotations

import importlib.metadata
from typing import Dict, List

from wxtools.core.base_plugin import BasePlugin

_cache: Dict[str, BasePlugin] = {}


def list_plugins() -> List[str]:
    eps = importlib.metadata.entry_points()
    group = eps.select(group="wxtools.plugins") if hasattr(eps, "select") else eps.get("wxtools.plugins", [])
    return [ep.name for ep in group]


def get_plugin(name: str) -> BasePlugin:
    if name in _cache:
        return _cache[name]
    eps = importlib.metadata.entry_points()
    group = eps.select(group="wxtools.plugins") if hasattr(eps, "select") else eps.get("wxtools.plugins", [])
    for ep in group:
        if ep.name == name:
            cls = ep.load()
            instance = cls()
            _cache[name] = instance
            return instance
    raise KeyError(f"Plugin '{name}' not found. Available: {list_plugins()}")
