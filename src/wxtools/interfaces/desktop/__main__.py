"""Desktop backend entry point — used by Electron app.

Starts the FastAPI backend in desktop mode and prints connection info
as a JSON line to stdout for the Electron process to parse.
"""

from __future__ import annotations

import json
import sys

from wxtools.runtime.app_host import start_server
from wxtools.runtime.bootstrap import bootstrap
from wxtools.runtime.paths import RuntimeMode


def main() -> None:
    """Initialize and start the desktop backend."""
    bootstrap(mode=RuntimeMode.DESKTOP)
    result = start_server(mode=RuntimeMode.DESKTOP, open_browser=False)
    # Print connection info as JSON for Electron to parse from stdout
    print(json.dumps(result))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
