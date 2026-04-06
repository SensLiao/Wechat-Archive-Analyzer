"""Tests for onboarding_service.check_onboarding_status."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from wxtools.application.onboarding_service import (
    OnboardingStep,
    OnboardingStatus,
    check_onboarding_status,
)
from wxtools.runtime.config import Config

# Patch targets — lazy imports inside check_onboarding_status resolve from
# the infrastructure modules, so we patch there.
_FIND_DIR = "wxtools.infrastructure.wechat.account_discovery.find_wechat_data_dir"
_DISCOVER = "wxtools.infrastructure.wechat.account_discovery.discover_accounts"


def _make_cfg(tmp_path: Path) -> Config:
    """Create a Config pointing to a temporary home directory."""
    home = tmp_path / ".wxtools"
    home.mkdir(parents=True, exist_ok=True)
    (home / "keys").mkdir(exist_ok=True)
    (home / "cache").mkdir(exist_ok=True)
    return Config(overrides={"_home": str(home), "wechat_data_dir": "auto"})


class TestNoWeChatInstalled:
    """WeChat data directory not found."""

    def test_returns_detect_wechat_step(self, tmp_path):
        cfg = _make_cfg(tmp_path)
        with patch(
            _FIND_DIR,
            return_value=None,
        ):
            status = check_onboarding_status(cfg)

        assert status.current_step == OnboardingStep.DETECT_WECHAT
        assert status.wechat_installed is False
        assert status.data_dir_found is False
        assert status.data_dir is None
        assert status.accounts_found == []
        assert status.is_complete is False

    def test_message_mentions_install(self, tmp_path):
        cfg = _make_cfg(tmp_path)
        with patch(
            _FIND_DIR,
            return_value=None,
        ):
            status = check_onboarding_status(cfg)

        assert "not found" in status.message.lower()


class TestWeChatFoundNoAccounts:
    """WeChat data dir exists but no account subfolders."""

    def test_returns_detect_accounts_step(self, tmp_path):
        cfg = _make_cfg(tmp_path)
        data_dir = tmp_path / "wechat_data"
        data_dir.mkdir()

        with patch(
            _FIND_DIR,
            return_value=data_dir,
        ), patch(
            _DISCOVER,
            return_value=[],
        ):
            status = check_onboarding_status(cfg)

        assert status.current_step == OnboardingStep.DETECT_ACCOUNTS
        assert status.wechat_installed is True
        assert status.data_dir_found is True
        assert status.data_dir == str(data_dir)
        assert status.accounts_found == []
        assert status.is_complete is False


class TestAccountsFoundNoKeys:
    """Accounts discovered but no decryption keys stored."""

    def test_returns_check_keys_step(self, tmp_path):
        cfg = _make_cfg(tmp_path)
        data_dir = tmp_path / "wechat_data"
        data_dir.mkdir()
        accounts = [
            {"wxid": "wxid_abc", "path": str(data_dir / "wxid_abc"), "db_dir": str(data_dir / "wxid_abc" / "db_storage"), "version": "4.x"},
        ]

        with patch(
            _FIND_DIR,
            return_value=data_dir,
        ), patch(
            _DISCOVER,
            return_value=accounts,
        ):
            status = check_onboarding_status(cfg)

        assert status.current_step == OnboardingStep.CHECK_KEYS
        assert status.accounts_found == accounts
        assert status.keys_available == []
        assert status.keys_missing == ["wxid_abc"]
        assert status.is_complete is False


class TestKeysStoredNotVerified:
    """Keys present but no decryption cache exists."""

    def test_returns_verify_decryption_step(self, tmp_path):
        cfg = _make_cfg(tmp_path)
        data_dir = tmp_path / "wechat_data"
        data_dir.mkdir()
        accounts = [
            {"wxid": "wxid_abc", "path": str(data_dir / "wxid_abc"), "db_dir": str(data_dir / "wxid_abc" / "db_storage"), "version": "4.x"},
        ]

        # Store a fake key
        from wxtools.infrastructure.secrets.keystore import Keystore
        ks = Keystore(cfg.keys_dir)
        ks.store_key("wechat", "wxid_abc", b"deadbeef" * 8, protection="password", password="test")

        with patch(
            _FIND_DIR,
            return_value=data_dir,
        ), patch(
            _DISCOVER,
            return_value=accounts,
        ):
            status = check_onboarding_status(cfg)

        assert status.current_step == OnboardingStep.VERIFY_DECRYPTION
        assert status.keys_available == ["wxid_abc"]
        assert status.keys_missing == []
        assert status.decryption_verified is False
        assert status.is_complete is False


class TestFullyReady:
    """Keys stored and decryption cache exists."""

    def test_returns_ready_step(self, tmp_path):
        cfg = _make_cfg(tmp_path)
        data_dir = tmp_path / "wechat_data"
        data_dir.mkdir()
        accounts = [
            {"wxid": "wxid_abc", "path": str(data_dir / "wxid_abc"), "db_dir": str(data_dir / "wxid_abc" / "db_storage"), "version": "4.x"},
        ]

        # Store a fake key
        from wxtools.infrastructure.secrets.keystore import Keystore
        ks = Keystore(cfg.keys_dir)
        ks.store_key("wechat", "wxid_abc", b"deadbeef" * 8, protection="password", password="test")

        # Create decryption cache with a file in it
        cache_dir = cfg.cache_dir / "wxid_abc"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "message_0.db").write_text("fake")

        with patch(
            _FIND_DIR,
            return_value=data_dir,
        ), patch(
            _DISCOVER,
            return_value=accounts,
        ):
            status = check_onboarding_status(cfg)

        assert status.current_step == OnboardingStep.READY
        assert status.wechat_installed is True
        assert status.data_dir_found is True
        assert status.keys_available == ["wxid_abc"]
        assert status.decryption_verified is True
        assert status.is_complete is True
        assert "complete" in status.message.lower()


class TestMultipleAccounts:
    """Mixed state: one account with key, one without."""

    def test_partial_keys_still_progresses(self, tmp_path):
        cfg = _make_cfg(tmp_path)
        data_dir = tmp_path / "wechat_data"
        data_dir.mkdir()
        accounts = [
            {"wxid": "wxid_abc", "path": str(data_dir / "wxid_abc"), "db_dir": str(data_dir / "wxid_abc" / "db_storage"), "version": "4.x"},
            {"wxid": "wxid_def", "path": str(data_dir / "wxid_def"), "db_dir": str(data_dir / "wxid_def" / "db_storage"), "version": "4.x"},
        ]

        # Store key only for one account
        from wxtools.infrastructure.secrets.keystore import Keystore
        ks = Keystore(cfg.keys_dir)
        ks.store_key("wechat", "wxid_abc", b"deadbeef" * 8, protection="password", password="test")

        with patch(
            _FIND_DIR,
            return_value=data_dir,
        ), patch(
            _DISCOVER,
            return_value=accounts,
        ):
            status = check_onboarding_status(cfg)

        # Should progress past CHECK_KEYS since at least one key exists
        assert status.current_step in (OnboardingStep.VERIFY_DECRYPTION, OnboardingStep.READY)
        assert "wxid_abc" in status.keys_available
        assert "wxid_def" in status.keys_missing


class TestExplicitDataDir:
    """Config has an explicit wechat_data_dir (not 'auto')."""

    def test_uses_explicit_dir(self, tmp_path):
        data_dir = tmp_path / "explicit_data"
        data_dir.mkdir()
        cfg = Config(overrides={
            "_home": str(tmp_path / ".wxtools"),
            "wechat_data_dir": str(data_dir),
        })
        (tmp_path / ".wxtools" / "keys").mkdir(parents=True)
        (tmp_path / ".wxtools" / "cache").mkdir(parents=True)

        with patch(
            _DISCOVER,
            return_value=[],
        ) as mock_discover:
            status = check_onboarding_status(cfg)

        mock_discover.assert_called_once_with(str(data_dir))
        assert status.wechat_installed is True
        assert status.data_dir == str(data_dir)
