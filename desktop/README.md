# wxtools Desktop (Electron + PyInstaller)

Electron shell that wraps the wxtools Python backend into a native desktop application with a bundled installer.

## Architecture

```
Electron (main.js)
  └── spawns wxtools-backend executable (PyInstaller bundle)
        └── FastAPI server serving the React frontend
              └── web/dist/ (Vite build, included as extraResource)
```

1. Electron spawns the bundled `wxtools-backend` executable
2. Backend prints JSON connection info to stdout: `{"host": "...", "port": ..., "token": "..."}`
3. Electron parses the JSON and opens a BrowserWindow pointing to the backend URL
4. On quit, Electron sends SIGTERM to the backend process

## Development

### Prerequisites

- **Node.js** 18+ with npm
- **Python** 3.10+ with wxtools installed (`pip install -e .` from repo root)

### Run (dev mode)

```bash
cd desktop
npm install
npm start
```

In dev mode, `main.js` detects that the app is not packaged and runs `python -m wxtools.interfaces.desktop` directly instead of looking for a bundled executable.

## Building the Installer

### Full pipeline (recommended)

```bash
# From repo root:
python desktop/scripts/build.py
```

This runs all four steps:
1. `npm run build` in `web/` to produce the frontend
2. Copies frontend to PyInstaller output directory
3. Runs PyInstaller to bundle the Python backend
4. Runs electron-builder to create the Windows NSIS installer

### Partial builds

```bash
python desktop/scripts/build.py --skip-frontend    # reuse existing web/dist/
python desktop/scripts/build.py --skip-backend      # reuse existing PyInstaller output
python desktop/scripts/build.py --skip-installer    # bundle backend only, no installer
```

### Manual step-by-step

```bash
# 1. Build web frontend
cd web && npm run build && cd ..

# 2. Bundle Python backend
pip install pyinstaller
pyinstaller desktop/build/wxtools-backend.spec

# 3. Build Electron installer
cd desktop
npm install
npm run build
```

Output goes to `desktop/dist/`.

### Prerequisites for building

- **PyInstaller**: `pip install pyinstaller`
- **electron-builder**: installed via `npm install` in `desktop/`
- **SQLCipher DLL** (optional): If using pysqlcipher3, the DLL is typically included in the wheel. If not, add the DLL path to the `.spec` file's `binaries` list. See comments in `build/wxtools-backend.spec`.

## Directory Structure

```
desktop/
├── main.js                      # Electron main process
├── package.json                 # Electron + electron-builder config
├── README.md
├── assets/                      # Icons (create before building)
│   ├── icon.ico                 # Windows icon (256x256)
│   └── icon.icns                # macOS icon
├── build/
│   ├── wxtools-backend.spec     # PyInstaller spec file
│   └── pyinstaller-output/      # PyInstaller build output (gitignored)
├── scripts/
│   └── build.py                 # Build orchestration script
└── dist/                        # Installer output (gitignored)
```

## Notes

- The `assets/` directory with icon files must be created before building the installer. Without icons, electron-builder will warn but still produce a working installer.
- The backend executable is ~50-80 MB (PyInstaller bundles Python + all dependencies).
- On Windows, NSIS creates a standard installer with Start Menu shortcuts.
- The `build/pyinstaller-output/` and `dist/` directories should be gitignored.
