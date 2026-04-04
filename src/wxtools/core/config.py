"""Configuration loading and validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

DEFAULTS: Dict[str, Any] = {
    "wechat_data_dir": "auto",
    "active_account": "auto",
    "sqlcipher_path": "sqlcipher",
    "cache_dir": "",
    "log_level": "WARNING",
    "default_limit": 100,
    "query_timeout": 30,
    "keystore_protection": "dpapi",
    "output_language": "zh",
}

ENV_MAP: Dict[str, str] = {
    "wechat_data_dir": "WXTOOLS_WECHAT_DATA_DIR",
    "active_account": "WXTOOLS_ACCOUNT",
    "sqlcipher_path": "WXTOOLS_SQLCIPHER_PATH",
    "cache_dir": "WXTOOLS_CACHE_DIR",
    "log_level": "WXTOOLS_LOG_LEVEL",
    "output_language": "WXTOOLS_LANG",
}

VALIDATORS = {
    "default_limit": lambda v: max(1, min(int(v), 10000)),
    "query_timeout": lambda v: max(1, min(int(v), 300)),
    "log_level": lambda v: v.upper() if v.upper() in ("DEBUG", "INFO", "WARNING", "ERROR", "NONE") else "WARNING",
}


class Config:
    """Layered configuration: defaults -> YAML file -> env vars -> overrides."""

    def __init__(self, file_values: Optional[Dict[str, Any]] = None, overrides: Optional[Dict[str, Any]] = None):
        self._data: Dict[str, Any] = dict(DEFAULTS)
        if file_values:
            self._data.update(file_values)
        for key, env_name in ENV_MAP.items():
            val = os.environ.get(env_name)
            if val is not None:
                self._data[key] = val
        if overrides:
            self._data.update(overrides)
        self._validate()

    def _validate(self) -> None:
        for key, validator in VALIDATORS.items():
            if key in self._data:
                self._data[key] = validator(self._data[key])

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    @property
    def home_dir(self) -> Path:
        custom = self._data.get("_home")
        if custom:
            return Path(custom)
        return Path.home() / ".wxtools"

    @property
    def cache_dir(self) -> Path:
        cd = self._data.get("cache_dir")
        if cd:
            return Path(cd)
        return self.home_dir / "cache"

    @property
    def keys_dir(self) -> Path:
        return self.home_dir / "keys"

    @property
    def logs_dir(self) -> Path:
        return self.home_dir / "logs"

    @property
    def session_dir(self) -> Path:
        return self.home_dir / "session"

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self._data.items() if not k.startswith("_")}


def load_config(home: Optional[Path] = None) -> Config:
    """Load config from YAML file + env vars."""
    if home is None:
        home = Path.home() / ".wxtools"
    config_file = home / "config.yaml"
    file_values: Dict[str, Any] = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            file_values = yaml.safe_load(f) or {}
    return Config(file_values=file_values, overrides={"_home": str(home)})
