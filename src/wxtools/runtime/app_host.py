"""Application host — starts the FastAPI backend in CLI or Desktop mode."""

from __future__ import annotations

import logging
import secrets
import socket
import webbrowser
from pathlib import Path
from typing import Optional

from wxtools.runtime.paths import RuntimeMode

logger = logging.getLogger("wxtools.runtime.app_host")


def find_free_port(host: str = "127.0.0.1") -> int:
    """Find a free TCP port by binding to port 0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def start_server(
    mode: RuntimeMode = RuntimeMode.CLI,
    host: str = "127.0.0.1",
    port: Optional[int] = None,
    open_browser: bool = True,
) -> dict:
    """Start the wxtools backend server.

    For Desktop mode, auto-selects a free port and returns connection info
    without blocking (intended for Electron IPC).

    For CLI mode, runs uvicorn in the foreground (blocking).

    Returns:
        Dict with keys: host, port, token, url.
    """
    import uvicorn

    from wxtools.interfaces.api.app import create_app

    if port is None:
        port = find_free_port(host) if mode == RuntimeMode.DESKTOP else 8808

    # Determine static dir — look for built frontend
    static_dir = Path(__file__).resolve().parents[2] / "web" / "dist"
    if not static_dir.is_dir():
        static_dir = None

    app_instance, token = create_app(static_dir=static_dir)

    url = f"http://{host}:{port}"

    connection_info = {
        "host": host,
        "port": port,
        "token": token,
        "url": url,
    }

    if mode == RuntimeMode.DESKTOP:
        # Desktop mode: start in a background thread and return immediately
        import threading

        server = uvicorn.Server(
            uvicorn.Config(app_instance, host=host, port=port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        logger.info("Desktop backend started at %s", url)
        return connection_info

    # CLI mode: print info and run blocking
    logger.info("Starting Web App at %s", url)

    if open_browser:
        webbrowser.open(f"{url}?token={token}")

    uvicorn.run(app_instance, host=host, port=port, log_level="info")
    return connection_info
