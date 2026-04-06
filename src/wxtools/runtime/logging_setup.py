"""Logging configuration with sensitive data redaction."""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_HEX_KEY_PATTERN = re.compile(r"[0-9a-fA-F]{64}")


class RedactionFilter(logging.Filter):
    """Redact sensitive data from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _HEX_KEY_PATTERN.sub(
                lambda m: m.group()[:8] + "..." + m.group()[-4:],
                record.msg,
            )
        return True


def setup_logging(
    verbosity: int = 0,
    json_mode: bool = False,
    log_dir: Optional[Path] = None,
) -> logging.Logger:
    logger = logging.getLogger("wxtools")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    stderr_level = {0: logging.WARNING, 1: logging.INFO}.get(verbosity, logging.DEBUG)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(stderr_level)
    stderr_fmt = "%(message)s" if json_mode else "%(levelname)s: %(message)s"
    stderr_handler.setFormatter(logging.Formatter(stderr_fmt))
    stderr_handler.addFilter(RedactionFilter())
    logger.addHandler(stderr_handler)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "wxtools.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        file_handler.addFilter(RedactionFilter())
        logger.addHandler(file_handler)

    return logger
