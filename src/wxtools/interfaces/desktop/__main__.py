"""Desktop backend entry point — used by Electron app.

Starts the FastAPI backend in desktop mode and prints connection info
as a JSON line to stdout for the Electron process to parse.
"""

from __future__ import annotations

import json
import signal
import sys
import threading

from wxtools.runtime.app_host import start_server
from wxtools.runtime.bootstrap import bootstrap
from wxtools.runtime.paths import RuntimeMode

_shutdown = threading.Event()


def main() -> None:
    """Initialize and start the desktop backend."""
    bootstrap(mode=RuntimeMode.DESKTOP)
    result = start_server(mode=RuntimeMode.DESKTOP, open_browser=False)
    # Print connection info as JSON for Electron to parse from stdout
    print(json.dumps(result))
    sys.stdout.flush()

    # Keep the main thread alive so the daemon uvicorn thread keeps running.
    # Electron sends SIGTERM on quit which will unblock the wait.
    signal.signal(signal.SIGTERM, lambda *_: _shutdown.set())
    signal.signal(signal.SIGINT, lambda *_: _shutdown.set())
    _shutdown.wait()


if __name__ == "__main__":
    main()
