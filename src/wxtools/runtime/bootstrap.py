"""Application initialization for CLI and Desktop modes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from wxtools.runtime.config import Config, load_config
from wxtools.runtime.logging_setup import setup_logging
from wxtools.runtime.paths import AppPaths, RuntimeMode


def bootstrap(
    mode: RuntimeMode = RuntimeMode.CLI,
    verbosity: int = 0,
    json_mode: bool = False,
    home: Optional[Path] = None,
) -> tuple[Config, AppPaths]:
    """Initialize the application — config + logging + paths.

    Args:
        mode: Runtime mode determining path layout.
        verbosity: Log verbosity (0=WARNING, 1=INFO, 2+=DEBUG).
        json_mode: If True, use JSON-friendly log format.
        home: Override the home directory (useful for testing and DEV mode).

    Returns:
        Tuple of (Config, AppPaths).
    """
    paths = AppPaths(mode=mode, home=home)
    cfg = load_config(paths.home_dir)
    setup_logging(verbosity=verbosity, json_mode=json_mode, log_dir=paths.logs_dir)
    return cfg, paths
