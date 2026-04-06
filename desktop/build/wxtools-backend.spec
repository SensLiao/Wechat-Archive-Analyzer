# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for wxtools desktop backend.

Bundles the Python backend into a single-directory executable that
the Electron shell spawns as a sidecar process.

Usage:
    cd <repo-root>
    pyinstaller desktop/build/wxtools-backend.spec

Prerequisites:
    pip install pyinstaller
    pip install -e .          # wxtools must be installed first

Notes on SQLCipher:
    The pysqlcipher3 package requires the SQLCipher DLL at runtime.
    - If using pysqlcipher3, the DLL is typically bundled inside the
      pysqlcipher3 wheel. PyInstaller should pick it up automatically.
    - If using a standalone sqlcipher CLI, add it manually:
          binaries=[('path/to/sqlcipher.exe', '.')]
    - If the DLL is not found at runtime, wxtools falls back to the
      CLI-based decryption backend (slower but no DLL needed).
"""

import os
import sys
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis

# Resolve repo root (spec file is at desktop/build/)
REPO_ROOT = Path(SPECPATH).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

a = Analysis(
    # Entry point: the desktop __main__.py
    [str(SRC_DIR / "wxtools" / "interfaces" / "desktop" / "__main__.py")],
    pathex=[str(SRC_DIR)],
    binaries=[
        # NOTE: Add SQLCipher DLL here if needed, e.g.:
        # (r'C:\path\to\sqlcipher.dll', '.'),
    ],
    datas=[
        # Include any data files wxtools needs at runtime.
        # The web frontend is NOT bundled here — it's an Electron extraResource.
    ],
    hiddenimports=[
        # wxtools package tree (V6 layered architecture)
        "wxtools",
        "wxtools.domain",
        "wxtools.domain.schema",
        "wxtools.domain.errors",
        "wxtools.runtime",
        "wxtools.runtime.config",
        "wxtools.runtime.logging_setup",
        "wxtools.runtime.platform",
        "wxtools.runtime.bootstrap",
        "wxtools.runtime.paths",
        "wxtools.runtime.app_host",
        "wxtools.infrastructure",
        "wxtools.infrastructure.wechat",
        "wxtools.infrastructure.wechat.account_discovery",
        "wxtools.infrastructure.wechat.db_reader",
        "wxtools.infrastructure.wechat.decryptor",
        "wxtools.infrastructure.wechat.key_extractor",
        "wxtools.infrastructure.wechat.key_validator",
        "wxtools.infrastructure.wechat.schema_mapper",
        "wxtools.infrastructure.wechat.fts_index",
        "wxtools.infrastructure.wechat.sns_reader",
        "wxtools.infrastructure.wechat.attachment_resolver",
        "wxtools.infrastructure.secrets",
        "wxtools.infrastructure.secrets.keystore",
        "wxtools.infrastructure.secrets.unlock_session",
        "wxtools.infrastructure.secrets.backends",
        "wxtools.infrastructure.storage",
        "wxtools.infrastructure.exporters",
        "wxtools.application",
        "wxtools.application.account_service",
        "wxtools.application.key_service",
        "wxtools.application.query_service",
        "wxtools.application.export_service",
        "wxtools.application.cache_service",
        "wxtools.application.home_service",
        "wxtools.application.workspace_service",
        "wxtools.application.onboarding_service",
        "wxtools.interfaces.desktop",
        "wxtools.interfaces.api",
        "wxtools.interfaces.api.app",
        # FastAPI / Uvicorn dependencies that PyInstaller may miss
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "starlette",
        "pydantic",
        "click",
        "yaml",
        "psutil",
        "cryptography",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude dev-only packages to reduce size
        "pytest",
        "ruff",
        "black",
        "mypy",
        "pyright",
        "tkinter",
        "matplotlib",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="wxtools-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Must be True — Electron reads stdout for connection info
    # NOTE: Add icon here for branding:
    # icon=str(REPO_ROOT / 'desktop' / 'assets' / 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="wxtools-backend",
)
