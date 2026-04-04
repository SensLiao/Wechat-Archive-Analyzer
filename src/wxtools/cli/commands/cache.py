"""Cache management commands."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import click

from wxtools.cli.output import error_envelope, print_json, success_envelope
from wxtools.core.config import load_config
from wxtools.core.errors import CacheEmptyError, WxToolsError
from wxtools.plugins.wechat.fts_index import FtsIndex

logger = logging.getLogger("wxtools.cli.cache")


def _dir_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    if path.is_dir():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def _format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


@click.group()
def cache():
    """Manage decrypted database cache."""
    pass


@cache.command()
@click.pass_context
def status(ctx):
    """Show cache status."""
    state = ctx.obj
    cfg = load_config()
    cache_dir = cfg.cache_dir

    accounts = []
    if cache_dir.is_dir():
        for child in sorted(cache_dir.iterdir()):
            if child.is_dir():
                size = _dir_size(child)
                db_count = len(list(child.rglob("*.db")))
                # Read cache metadata if available
                meta_file = child / ".cache_meta.json"
                decrypted_at = None
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                        decrypted_at = meta.get("decrypted_at")
                    except (json.JSONDecodeError, OSError):
                        pass

                # Fallback: use dir mtime
                if not decrypted_at:
                    mtime = child.stat().st_mtime
                    decrypted_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

                accounts.append({
                    "wxid": child.name,
                    "path": str(child),
                    "size_bytes": size,
                    "size_human": _format_size(size),
                    "db_count": db_count,
                    "decrypted_at": decrypted_at,
                })

    total_size = sum(a["size_bytes"] for a in accounts)

    if state.json_mode:
        print_json(success_envelope(
            {
                "cache_dir": str(cache_dir),
                "accounts": accounts,
                "total_size_bytes": total_size,
                "total_size_human": _format_size(total_size),
            },
            command="cache status",
        ))
    else:
        if not accounts:
            click.echo(f"Cache directory: {cache_dir}")
            click.echo("No cached data.")
        else:
            click.echo(f"Cache directory: {cache_dir}")
            click.echo(f"Total size: {_format_size(total_size)}\n")
            for acc in accounts:
                click.echo(f"  {acc['wxid']}:")
                click.echo(f"    Size: {acc['size_human']} ({acc['db_count']} databases)")
                click.echo(f"    Decrypted: {acc['decrypted_at']}")


@cache.command()
@click.option("--account", help="Clear cache for specific account.")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
@click.pass_context
def clear(ctx, account, yes):
    """Clear decrypted cache."""
    state = ctx.obj
    cfg = load_config()
    cache_dir = cfg.cache_dir

    if not cache_dir.is_dir():
        if state.json_mode:
            e = CacheEmptyError()
            print_json(error_envelope(e.code, e.message, e.remediation, command="cache clear"))
        else:
            click.echo("No cache to clear.")
        return

    if account:
        target = cache_dir / account
        if not target.is_dir():
            if state.json_mode:
                e = CacheEmptyError()
                print_json(error_envelope(e.code, e.message, e.remediation, command="cache clear"))
            else:
                click.echo(f"No cache found for account {account}.")
            return
        size = _dir_size(target)
        if not yes:
            if state.json_mode:
                # In JSON mode without --yes, report what would be cleared
                print_json(error_envelope(
                    "EXPORT_CONFIRM_REQUIRED",
                    f"Cache for {account} ({_format_size(size)}) will be deleted.",
                    "Add --yes to confirm.",
                    command="cache clear",
                ))
                ctx.exit(8)
                return
            click.confirm(f"Delete cache for {account} ({_format_size(size)})?", abort=True)
        shutil.rmtree(target)
        if state.json_mode:
            print_json(success_envelope(
                {"cleared": account, "freed_bytes": size},
                command="cache clear",
            ))
        else:
            click.echo(f"Cache cleared for {account} ({_format_size(size)} freed).")
    else:
        size = _dir_size(cache_dir)
        if not yes:
            if state.json_mode:
                print_json(error_envelope(
                    "EXPORT_CONFIRM_REQUIRED",
                    f"All cache ({_format_size(size)}) will be deleted.",
                    "Add --yes to confirm.",
                    command="cache clear",
                ))
                ctx.exit(8)
                return
            click.confirm(f"Delete all cached data ({_format_size(size)})?", abort=True)
        for child in cache_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            elif child.is_file():
                child.unlink()
        if state.json_mode:
            print_json(success_envelope(
                {"cleared": "all", "freed_bytes": size},
                command="cache clear",
            ))
        else:
            click.echo(f"All cache cleared ({_format_size(size)} freed).")


def _resolve_cache_dir(cfg, account):
    """Resolve the cache directory for a given account (or auto-detect first one)."""
    cache_base = cfg.cache_dir
    if account:
        d = cache_base / account
        return d if d.is_dir() else None
    # Auto: find first account subdir
    if cache_base.is_dir():
        for child in sorted(cache_base.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                return child
    return None


@cache.command("build-index")
@click.option("--account", default=None, help="Account wxid to index.")
@click.pass_context
def build_index(ctx, account):
    """Build full-text search index for cached messages."""
    state = ctx.obj
    cfg = load_config()
    cache_dir = _resolve_cache_dir(cfg, account)

    if cache_dir is None:
        if state.json_mode:
            e = CacheEmptyError()
            print_json(error_envelope(e.code, e.message, e.remediation, command="cache build-index"))
        else:
            click.echo("No cached data found.")
        ctx.exit(1)
        return

    if not state.json_mode:
        click.echo("正在建立搜索索引...")

    idx = FtsIndex(cache_dir)
    stats = idx.build()

    if state.json_mode:
        print_json(success_envelope(
            {"account": cache_dir.name, "indexed": stats["indexed"]},
            command="cache build-index",
        ))
    else:
        click.echo(f"索引建立完成，共 {stats['indexed']} 条消息。")


@cache.command("drop-index")
@click.option("--account", default=None, help="Account wxid to drop index for.")
@click.pass_context
def drop_index(ctx, account):
    """Remove full-text search index."""
    state = ctx.obj
    cfg = load_config()
    cache_dir = _resolve_cache_dir(cfg, account)

    if cache_dir is None:
        if state.json_mode:
            e = CacheEmptyError()
            print_json(error_envelope(e.code, e.message, e.remediation, command="cache drop-index"))
        else:
            click.echo("No cached data found.")
        ctx.exit(1)
        return

    idx = FtsIndex(cache_dir)
    idx.drop()

    if state.json_mode:
        print_json(success_envelope(
            {"account": cache_dir.name, "dropped": True},
            command="cache drop-index",
        ))
    else:
        click.echo("搜索索引已删除。")
