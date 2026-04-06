"""JSON envelope formatting for CLI output."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import wxtools


def success_envelope(data: dict, command: str = "") -> dict:
    return {
        "ok": True,
        "data": data,
        "meta": {
            "command": command,
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
            "version": wxtools.__version__,
        },
    }


def error_envelope(code: str, message: str, remediation: str, command: str = "", **extra) -> dict:
    err = {"code": code, "message": message, "remediation": remediation}
    err.update(extra)
    return {
        "ok": False,
        "error": err,
        "meta": {
            "command": command,
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
            "version": wxtools.__version__,
        },
    }


def print_json(envelope: dict) -> None:
    stream = sys.stdout if envelope.get("ok") else sys.stderr
    print(json.dumps(envelope, ensure_ascii=False, indent=2), file=stream)
