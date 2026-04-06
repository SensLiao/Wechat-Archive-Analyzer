"""Platform-specific secret protection backends."""
from __future__ import annotations

from typing import List

from wxtools.runtime.platform import get_default_backend_name
from wxtools.infrastructure.secrets.backends.dpapi import DpapiBackend
from wxtools.infrastructure.secrets.backends.linux_secret_service import LinuxSecretServiceBackend
from wxtools.infrastructure.secrets.backends.macos_keychain import MacosKeychainBackend
from wxtools.infrastructure.secrets.backends.password_file import PasswordFileBackend

_REGISTRY = {
    "windows-dpapi": lambda **kw: DpapiBackend(),
    "macos-keychain": lambda **kw: MacosKeychainBackend(),
    "linux-secret-service": lambda **kw: LinuxSecretServiceBackend(),
    "password-file": lambda **kw: PasswordFileBackend(password=_require_password(kw)),
}


def _require_password(kw: dict) -> str:
    pw = kw.get("password")
    if not pw:
        from wxtools.domain.errors import KeyPasswordWrongError
        raise KeyPasswordWrongError()
    return pw


def get_backend(name: str, **kwargs):
    """Instantiate a secret backend by name. Pass name="auto" for platform default."""
    if name == "auto":
        name = get_default_backend_name()
    factory = _REGISTRY.get(name)
    if factory is None:
        raise ValueError(f"Unknown secret backend: '{name}'. Available: {list(_REGISTRY)}")
    return factory(**kwargs)


def list_backends() -> List[str]:
    """Return all registered backend names."""
    return list(_REGISTRY.keys())
