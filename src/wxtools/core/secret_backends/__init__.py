"""Platform-specific secret protection backends."""
from __future__ import annotations

from typing import List

from wxtools.core.platform import get_default_backend_name
from wxtools.core.secret_backends.dpapi import DpapiBackend
from wxtools.core.secret_backends.linux_secret_service import LinuxSecretServiceBackend
from wxtools.core.secret_backends.macos_keychain import MacosKeychainBackend
from wxtools.core.secret_backends.password_file import PasswordFileBackend

_REGISTRY = {
    "windows-dpapi": lambda **kw: DpapiBackend(),
    "macos-keychain": lambda **kw: MacosKeychainBackend(),
    "linux-secret-service": lambda **kw: LinuxSecretServiceBackend(),
    "password-file": lambda **kw: PasswordFileBackend(password=kw["password"]),
}


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
