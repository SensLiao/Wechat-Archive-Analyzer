#!/usr/bin/env python3
"""Build orchestration script for wxtools desktop installer.

Runs the full pipeline:
  1. Build web frontend (Vite)
  2. Copy built frontend to Electron extraResources location
  3. Run PyInstaller to bundle Python backend
  4. Run electron-builder to create the installer

Usage:
    python desktop/scripts/build.py          # full build
    python desktop/scripts/build.py --skip-frontend   # skip web build
    python desktop/scripts/build.py --skip-backend    # skip PyInstaller
    python desktop/scripts/build.py --skip-installer  # skip electron-builder

Prerequisites:
    - Node.js 18+ and npm
    - Python 3.9+ with wxtools installed (pip install -e .)
    - PyInstaller: pip install pyinstaller
    - Electron + electron-builder: cd desktop && npm install
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Resolve project paths
SCRIPT_DIR = Path(__file__).resolve().parent
DESKTOP_DIR = SCRIPT_DIR.parent
REPO_ROOT = DESKTOP_DIR.parent
WEB_DIR = REPO_ROOT / "web"
WEB_DIST = WEB_DIR / "dist"
SPEC_FILE = DESKTOP_DIR / "build" / "wxtools-backend.spec"
PYINSTALLER_OUTPUT = DESKTOP_DIR / "build" / "pyinstaller-output"
BACKEND_DIST = PYINSTALLER_OUTPUT / "wxtools-backend"


def run(cmd: list[str], cwd: Path, label: str) -> None:
    """Run a subprocess command, exit on failure."""
    print(f"\n{'='*60}")
    print(f"  [{label}]")
    print(f"  > {' '.join(cmd)}")
    print(f"  cwd: {cwd}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        print(f"\nERROR: [{label}] failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def step_build_frontend() -> None:
    """Step 1: Build the web frontend with Vite."""
    if not (WEB_DIR / "package.json").exists():
        print("ERROR: web/package.json not found. Is the web directory set up?")
        sys.exit(1)

    # Install dependencies if node_modules is missing
    if not (WEB_DIR / "node_modules").exists():
        run(["npm", "install"], cwd=WEB_DIR, label="Install web dependencies")

    run(["npm", "run", "build"], cwd=WEB_DIR, label="Build web frontend")

    if not WEB_DIST.exists():
        print("ERROR: web/dist/ was not created. Frontend build may have failed.")
        sys.exit(1)

    print(f"Frontend built successfully at {WEB_DIST}")


def step_copy_frontend() -> None:
    """Step 2: Copy built frontend to where electron-builder expects it.

    electron-builder.extraResources copies from ../web/dist to resources/frontend
    at packaging time. We also copy it alongside the PyInstaller output so the
    backend can serve it during development builds.
    """
    backend_frontend = PYINSTALLER_OUTPUT / "frontend"
    if backend_frontend.exists():
        shutil.rmtree(backend_frontend)

    if not WEB_DIST.exists():
        print("WARNING: web/dist/ not found. Skipping frontend copy.")
        print("         The backend will not be able to serve the frontend.")
        return

    shutil.copytree(str(WEB_DIST), str(backend_frontend))
    print(f"Frontend copied to {backend_frontend}")


def step_build_backend() -> None:
    """Step 3: Run PyInstaller to bundle the Python backend."""
    if not SPEC_FILE.exists():
        print(f"ERROR: PyInstaller spec not found at {SPEC_FILE}")
        sys.exit(1)

    # Ensure output directory exists
    PYINSTALLER_OUTPUT.mkdir(parents=True, exist_ok=True)

    run(
        [
            sys.executable, "-m", "PyInstaller",
            "--distpath", str(PYINSTALLER_OUTPUT),
            "--workpath", str(DESKTOP_DIR / "build" / "pyinstaller-work"),
            "--noconfirm",
            str(SPEC_FILE),
        ],
        cwd=REPO_ROOT,
        label="PyInstaller: bundle backend",
    )

    exe_path = BACKEND_DIST / "wxtools-backend.exe"
    if not exe_path.exists():
        # On non-Windows, the executable has no extension
        exe_path = BACKEND_DIST / "wxtools-backend"

    if exe_path.exists():
        print(f"Backend bundled at {exe_path}")
    else:
        print(f"WARNING: Expected executable not found at {BACKEND_DIST}")
        print("         Check PyInstaller output for errors.")


def step_build_installer() -> None:
    """Step 4: Run electron-builder to create the distributable installer."""
    if not (DESKTOP_DIR / "node_modules").exists():
        run(["npm", "install"], cwd=DESKTOP_DIR, label="Install desktop dependencies")

    run(
        ["npm", "run", "build"],
        cwd=DESKTOP_DIR,
        label="electron-builder: create installer",
    )

    dist_dir = DESKTOP_DIR / "dist"
    if dist_dir.exists():
        installers = list(dist_dir.glob("*.exe")) + list(dist_dir.glob("*.dmg"))
        if installers:
            print(f"\nInstaller(s) created:")
            for f in installers:
                print(f"  {f}")
        else:
            print(f"\nInstaller output directory: {dist_dir}")
            print("  (check for .exe or .dmg files)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build wxtools desktop installer"
    )
    parser.add_argument(
        "--skip-frontend", action="store_true",
        help="Skip web frontend build (assumes web/dist/ exists)"
    )
    parser.add_argument(
        "--skip-backend", action="store_true",
        help="Skip PyInstaller backend bundling"
    )
    parser.add_argument(
        "--skip-installer", action="store_true",
        help="Skip electron-builder installer creation"
    )
    args = parser.parse_args()

    print("wxtools Desktop Build Pipeline")
    print(f"  Repo root:  {REPO_ROOT}")
    print(f"  Desktop:    {DESKTOP_DIR}")
    print(f"  Web:        {WEB_DIR}")

    # Step 1: Build frontend
    if not args.skip_frontend:
        step_build_frontend()
    else:
        print("\n[SKIP] Frontend build")

    # Step 2: Copy frontend assets
    if not args.skip_backend:
        step_copy_frontend()

    # Step 3: Bundle backend
    if not args.skip_backend:
        step_build_backend()
    else:
        print("\n[SKIP] Backend bundling")

    # Step 4: Create installer
    if not args.skip_installer:
        step_build_installer()
    else:
        print("\n[SKIP] Installer creation")

    print("\n" + "="*60)
    print("  Build pipeline complete!")
    print("="*60)


if __name__ == "__main__":
    main()
