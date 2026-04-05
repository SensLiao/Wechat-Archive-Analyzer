# wxtools Desktop (Electron PoC)

Minimal Electron shell that wraps the wxtools local web app into a native desktop window.

## How it works

1. Spawns the Python backend as a sidecar: `python -X utf8 -m wxtools app start --no-open --port 8808`
2. Polls `GET /api/health` until the backend is ready (up to 15 seconds)
3. Opens a BrowserWindow pointing to `http://127.0.0.1:8808`
4. Kills the Python process when the window closes

## Prerequisites

- **Node.js** 18+
- **Python** 3.10+ with wxtools installed (`pip install -e .` from repo root)

## Run (development)

```bash
cd desktop
npm install
npm start
```

## Build (distributable)

```bash
npm run build
```

Output goes to `desktop/dist/`. The build bundles the frontend from `web/dist/` as an extra resource.

## Notes

- This is a **proof-of-concept**. For a production desktop app, consider Tauri (Rust-based, smaller binary, lower memory) or PyInstaller bundling.
- The Electron shell does not bundle Python itself. Users must have Python + wxtools available on PATH.
- Session token is parsed from backend stdout and passed as a query parameter.
