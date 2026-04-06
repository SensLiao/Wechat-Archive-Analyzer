"""Tests for wxtools.runtime.bootstrap."""

from __future__ import annotations

import logging
from pathlib import Path

from wxtools.runtime.bootstrap import bootstrap
from wxtools.runtime.config import Config
from wxtools.runtime.paths import AppPaths, RuntimeMode


class TestBootstrap:
    """bootstrap() initializes config, logging, and paths together."""

    def test_returns_config_and_paths(self, tmp_path):
        cfg, paths = bootstrap(mode=RuntimeMode.DEV, home=tmp_path / ".wxtools")
        assert isinstance(cfg, Config)
        assert isinstance(paths, AppPaths)

    def test_paths_reflect_mode_and_home(self, tmp_path):
        home = tmp_path / ".wxtools"
        _, paths = bootstrap(mode=RuntimeMode.DEV, home=home)
        assert paths.mode == RuntimeMode.DEV
        assert paths.home_dir == home

    def test_config_loaded_from_home(self, tmp_path):
        home = tmp_path / ".wxtools"
        home.mkdir(parents=True)
        config_file = home / "config.yaml"
        config_file.write_text("default_limit: 42\n")

        cfg, _ = bootstrap(mode=RuntimeMode.DEV, home=home)
        assert cfg.get("default_limit") == 42

    def test_logging_configured(self, tmp_path):
        home = tmp_path / ".wxtools"
        bootstrap(mode=RuntimeMode.DEV, home=home, verbosity=2)

        wxtools_logger = logging.getLogger("wxtools")
        # After bootstrap, logger should exist and have handlers
        assert wxtools_logger.level == logging.DEBUG

    def test_cli_mode_default(self, tmp_path):
        cfg, paths = bootstrap(mode=RuntimeMode.CLI, home=tmp_path / ".wxtools")
        assert paths.mode == RuntimeMode.CLI

    def test_desktop_mode(self, tmp_path):
        cfg, paths = bootstrap(mode=RuntimeMode.DESKTOP, home=tmp_path / ".wxtools")
        assert paths.mode == RuntimeMode.DESKTOP
        assert paths.home_dir == tmp_path / ".wxtools"

    def test_json_mode_does_not_crash(self, tmp_path):
        cfg, paths = bootstrap(
            mode=RuntimeMode.DEV, home=tmp_path / ".wxtools", json_mode=True
        )
        assert cfg is not None
