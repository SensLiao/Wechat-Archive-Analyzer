"""Allow running wxtools as `python -Xutf8 -m wxtools`.

On Chinese Windows, Python may crash during site.py init due to GBK encoding.
Using `python -Xutf8 -m wxtools` bypasses this by enabling UTF-8 mode before
site.py processes .pth files.
"""

from __future__ import annotations

import os


def main() -> None:
    # Ensure UTF-8 mode for any child processes or late imports
    os.environ["PYTHONUTF8"] = "1"

    from wxtools.cli.main import cli

    cli()


if __name__ == "__main__":
    main()
