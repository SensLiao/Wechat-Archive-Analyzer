"""First-run onboarding orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wxtools.runtime.config import Config

logger = logging.getLogger("wxtools.application.onboarding")


class OnboardingStep(Enum):
    DETECT_WECHAT = "detect_wechat"
    DETECT_ACCOUNTS = "detect_accounts"
    CHECK_KEYS = "check_keys"
    VERIFY_DECRYPTION = "verify_decryption"
    READY = "ready"


@dataclass
class OnboardingStatus:
    current_step: OnboardingStep
    wechat_installed: bool
    data_dir_found: bool
    data_dir: str | None
    accounts_found: list[dict[str, Any]]
    keys_available: list[str]
    keys_missing: list[str]
    decryption_verified: bool
    is_complete: bool
    message: str


def check_onboarding_status(cfg: Config) -> OnboardingStatus:
    """Run all onboarding checks and return current status.

    Walks through detection steps in order, stopping at the first
    incomplete step so callers know what action is required next.
    """
    from wxtools.infrastructure.wechat.account_discovery import (
        discover_accounts,
        find_wechat_data_dir,
    )
    from wxtools.infrastructure.secrets.keystore import Keystore

    # Step 1: Detect WeChat data directory
    data_dir_raw = cfg.get("wechat_data_dir", "auto")
    if data_dir_raw == "auto":
        data_dir_raw = find_wechat_data_dir()

    wechat_installed = data_dir_raw is not None
    data_dir_found = wechat_installed
    data_dir_str = str(data_dir_raw) if data_dir_raw else None

    if not wechat_installed:
        return OnboardingStatus(
            current_step=OnboardingStep.DETECT_WECHAT,
            wechat_installed=False,
            data_dir_found=False,
            data_dir=None,
            accounts_found=[],
            keys_available=[],
            keys_missing=[],
            decryption_verified=False,
            is_complete=False,
            message="WeChat data directory not found. Install WeChat and log in first.",
        )

    # Step 2: Discover accounts
    accounts = discover_accounts(data_dir_raw)
    if not accounts:
        return OnboardingStatus(
            current_step=OnboardingStep.DETECT_ACCOUNTS,
            wechat_installed=True,
            data_dir_found=True,
            data_dir=data_dir_str,
            accounts_found=[],
            keys_available=[],
            keys_missing=[],
            decryption_verified=False,
            is_complete=False,
            message="WeChat data directory found but no accounts detected. Log in to WeChat first.",
        )

    # Step 3: Check which accounts have stored keys
    ks = Keystore(cfg.keys_dir)
    account_wxids = [acc["wxid"] for acc in accounts]
    keys_available: list[str] = []
    keys_missing: list[str] = []

    for wxid in account_wxids:
        if ks.has_key("wechat", wxid):
            keys_available.append(wxid)
        else:
            keys_missing.append(wxid)

    if not keys_available:
        return OnboardingStatus(
            current_step=OnboardingStep.CHECK_KEYS,
            wechat_installed=True,
            data_dir_found=True,
            data_dir=data_dir_str,
            accounts_found=accounts,
            keys_available=[],
            keys_missing=keys_missing,
            decryption_verified=False,
            is_complete=False,
            message="Accounts found but no decryption keys stored. Extract keys with admin privileges while WeChat is running.",
        )

    # Step 4: Check if decryption cache exists for any account with keys
    cache_dir = cfg.cache_dir
    decryption_verified = False
    for wxid in keys_available:
        account_cache = cache_dir / wxid
        if account_cache.is_dir() and any(account_cache.iterdir()):
            decryption_verified = True
            break

    if not decryption_verified:
        return OnboardingStatus(
            current_step=OnboardingStep.VERIFY_DECRYPTION,
            wechat_installed=True,
            data_dir_found=True,
            data_dir=data_dir_str,
            accounts_found=accounts,
            keys_available=keys_available,
            keys_missing=keys_missing,
            decryption_verified=False,
            is_complete=False,
            message="Keys stored but decryption not yet verified. Run a query or verify the key to test decryption.",
        )

    # Step 5: Ready
    return OnboardingStatus(
        current_step=OnboardingStep.READY,
        wechat_installed=True,
        data_dir_found=True,
        data_dir=data_dir_str,
        accounts_found=accounts,
        keys_available=keys_available,
        keys_missing=keys_missing,
        decryption_verified=True,
        is_complete=True,
        message="Setup complete. Ready to query and export messages.",
    )
