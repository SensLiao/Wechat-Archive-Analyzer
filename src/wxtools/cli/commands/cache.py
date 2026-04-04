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
                db_count = len(list(child.glob("*.db")))
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
