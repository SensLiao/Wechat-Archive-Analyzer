"""Cache management application service.

Extracts cache business logic from the CLI layer into a framework-agnostic
service.  No Click dependency, no interactive prompts.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wxtools.core.errors import CacheEmptyError

if TYPE_CHECKING:
    from wxtools.core.config import Config

logger = logging.getLogger("wxtools.services.cache")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dir_size(path: Path) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    if path.is_dir():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def _format_size(size_bytes: int | float) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _resolve_cache_dir(cfg: Config, account: str | None) -> Path | None:
    """Resolve the cache directory for a given account (or first discovered)."""
    cache_base = cfg.cache_dir
    if account:
        d = cache_base / account
        return d if d.is_dir() else None
    if cache_base.is_dir():
        for child in sorted(cache_base.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                return child
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_status(cfg: Config) -> dict[str, Any]:
    """Return cache directory info and per-account statistics.

    Returns:
        Dict with ``cache_dir``, ``accounts`` list, ``total_size_bytes``,
        and ``total_size_human``.
    """
    cache_dir = cfg.cache_dir
    accounts: list[dict[str, Any]] = []

    if cache_dir.is_dir():
        for child in sorted(cache_dir.iterdir()):
            if child.is_dir():
                size = _dir_size(child)
                db_count = len(list(child.rglob("*.db")))

                # Read cache metadata if available
                meta_file = child / ".cache_meta.json"
                decrypted_at: str | None = None
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                        decrypted_at = meta.get("decrypted_at")
                    except (json.JSONDecodeError, OSError):
                        pass

                # Fallback: directory mtime
                if not decrypted_at:
                    mtime = child.stat().st_mtime
                    decrypted_at = datetime.fromtimestamp(
                        mtime, tz=timezone.utc
                    ).isoformat()

                accounts.append(
                    {
                        "wxid": child.name,
                        "path": str(child),
                        "size_bytes": size,
                        "size_human": _format_size(size),
                        "db_count": db_count,
                        "decrypted_at": decrypted_at,
                    }
                )

    total_size = sum(a["size_bytes"] for a in accounts)

    return {
        "cache_dir": str(cache_dir),
        "accounts": accounts,
        "total_size_bytes": total_size,
        "total_size_human": _format_size(total_size),
    }


def clear_cache(cfg: Config, account: str | None = None) -> dict[str, Any]:
    """Clear decrypted cache, optionally for a single account.

    Returns:
        Dict with ``cleared`` (account name or ``"all"``) and ``freed_bytes``.

    Raises:
        CacheEmptyError: When there is nothing to clear.
    """
    cache_dir = cfg.cache_dir

    if not cache_dir.is_dir():
        raise CacheEmptyError()

    if account:
        target = cache_dir / account
        if not target.is_dir():
            raise CacheEmptyError()
        size = _dir_size(target)
        shutil.rmtree(target)
        return {"cleared": account, "freed_bytes": size}

    size = _dir_size(cache_dir)
    if size == 0 and not any(cache_dir.iterdir()):
        raise CacheEmptyError()

    for child in cache_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        elif child.is_file():
            child.unlink()

    return {"cleared": "all", "freed_bytes": size}


def build_index(cfg: Config, account: str | None = None) -> dict[str, Any]:
    """Build the full-text search index for cached messages.

    Returns:
        Dict with ``account`` and ``indexed`` count.

    Raises:
        CacheEmptyError: When no cached data is found.
    """
    from wxtools.plugins.wechat.fts_index import FtsIndex

    cache_dir = _resolve_cache_dir(cfg, account)
    if cache_dir is None:
        raise CacheEmptyError()

    idx = FtsIndex(cache_dir)
    stats = idx.build()

    return {"account": cache_dir.name, "indexed": stats["indexed"]}


def drop_index(cfg: Config, account: str | None = None) -> dict[str, Any]:
    """Drop the full-text search index.

    Returns:
        Dict with ``account`` and ``dropped`` flag.

    Raises:
        CacheEmptyError: When no cached data is found.
    """
    from wxtools.plugins.wechat.fts_index import FtsIndex

    cache_dir = _resolve_cache_dir(cfg, account)
    if cache_dir is None:
        raise CacheEmptyError()

    idx = FtsIndex(cache_dir)
    idx.drop()

    return {"account": cache_dir.name, "dropped": True}
