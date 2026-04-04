"""Key management commands."""

from __future__ import annotations

import logging
import sys

import click

from wxtools.cli.output import error_envelope, print_json, success_envelope
from wxtools.core.config import load_config
from wxtools.core.errors import (
    AdminRequiredError,
    KeyNotFoundError,
    KeyPasswordWrongError,
    WeChatNotRunningError,
    WxToolsError,
)
from wxtools.core.keystore import Keystore

logger = logging.getLogger("wxtools.cli.key")


def _get_config_and_keystore(ctx: click.Context):
    state = ctx.obj
    cfg = load_config()
    ks = Keystore(cfg.keys_dir)
    return cfg, ks, state


def _resolve_account(cfg, account_arg: str | None) -> str | None:
    """Resolve account wxid from arg or config or auto-discover."""
    if account_arg:
        return account_arg
    active = cfg.get("active_account", "auto")
    if active != "auto":
        return active
    # Auto-discover
    from wxtools.plugins.wechat.account_discovery import discover_accounts, find_wechat_data_dir

    data_dir = cfg.get("wechat_data_dir", "auto")
    if data_dir == "auto":
        data_dir = find_wechat_data_dir()
    if not data_dir:
        return None
    accounts = discover_accounts(data_dir)
    if len(accounts) == 1:
        return accounts[0]["wxid"]
    return None


@click.group()
def key():
    """Manage WeChat decryption keys."""
    pass


@key.command()
@click.option("--account", help="Target account wxid.")
@click.pass_context
def extract(ctx, account):
    """Extract key from running WeChat process."""
    cfg, ks, state = _get_config_and_keystore(ctx)

    try:
        from wxtools.plugins.wechat.key_extractor import extract_keys
        from wxtools.plugins.wechat.account_discovery import (
            discover_accounts,
            find_wechat_data_dir,
        )

        # Resolve account and DB directory
        wxid = _resolve_account(cfg, account)
        data_dir = cfg.get("wechat_data_dir", "auto")
        if data_dir == "auto":
            data_dir = find_wechat_data_dir()

        db_dir = None
        if data_dir:
            accounts = discover_accounts(data_dir)
            for acc in accounts:
                if not wxid or acc["wxid"] == wxid:
                    wxid = acc["wxid"]
                    db_dir = acc["db_dir"]
                    break

        if not wxid:
            wxid = "unknown"
        if not db_dir:
            raise RuntimeError("Cannot find WeChat database directory")

        def _progress(msg: str) -> None:
            if not state.json_mode:
                click.echo(msg)

        if not state.json_mode:
            click.echo("Scanning WeChat process memory for encryption keys...")

        import json
        keys = extract_keys(db_dir, progress_fn=_progress)
        key_data = json.dumps(keys)

        # Determine protection mode
        config_protection = cfg.get("keystore_protection", "dpapi")
        is_first_time = not ks.has_key("wechat", wxid)
        password = None

        if config_protection != "dpapi":
            # Config explicitly sets non-default protection — respect it
            protection = config_protection
        elif is_first_time and not state.json_mode:
            # First-use password setup prompt (interactive only, one-time)
            click.echo()
            wants_password = click.confirm(
                "Do you want to set a password to protect your keys?\n"
                "(If not, Windows DPAPI will be used)",
                default=False,
            )
            if wants_password:
                password = click.prompt(
                    "Password", hide_input=True, confirmation_prompt=True
                )
                protection = "password"
            else:
                protection = "dpapi"
        else:
            # JSON mode or re-extraction: keep dpapi default
            protection = "dpapi"

        ks.store_key(
            "wechat", wxid, key_data.encode("ascii"),
            protection=protection, password=password,
        )

        if state.json_mode:
            print_json(success_envelope(
                {"account": wxid, "protection": protection, "status": "stored",
                 "db_count": len(keys)},
                command="key extract",
            ))
        else:
            click.echo(
                f"Extracted {len(keys)} database keys for account {wxid} "
                f"(protection: {protection})."
            )

    except (WxToolsError, OSError, RuntimeError) as e:
        if isinstance(e, WxToolsError):
            if state.json_mode:
                print_json(error_envelope(e.code, e.message, e.remediation, command="key extract"))
            else:
                click.echo(f"Error: {e.message}", err=True)
                click.echo(f"  Fix: {e.remediation}", err=True)
            ctx.exit(2 if isinstance(e, (AdminRequiredError, WeChatNotRunningError)) else 1)
        else:
            if state.json_mode:
                print_json(error_envelope(
                    "KEY_EXTRACT_FAILED", str(e),
                    "Ensure WeChat is running and terminal has admin privileges.",
                    command="key extract",
                ))
            else:
                click.echo(f"Error: {e}", err=True)
            ctx.exit(1)


@key.command()
@click.pass_context
def status(ctx):
    """Show stored key status."""
    cfg, ks, state = _get_config_and_keystore(ctx)

    keys = ks.list_keys()

    if state.json_mode:
        # Mask sensitive data — only show metadata
        safe_keys = []
        for k in keys:
            safe_keys.append({
                "wxid": k.get("wxid", ""),
                "plugin": k.get("plugin", ""),
                "protection": k.get("protection", ""),
                "created_at": k.get("created_at", ""),
                "last_verified": k.get("last_verified", ""),
            })
        print_json(success_envelope({"keys": safe_keys, "count": len(safe_keys)}, command="key status"))
    else:
        if not keys:
            click.echo("No stored keys. Run 'wxtools key extract' to extract a key.")
        else:
            click.echo(f"Stored keys ({len(keys)}):")
            for k in keys:
                wxid = k.get("wxid", "unknown")
                prot = k.get("protection", "?")
                created = k.get("created_at", "?")
                click.echo(f"  {wxid} — {prot} protection, created {created}")


@key.command(name="set-password")
@click.option("--account", help="Target account wxid.")
@click.pass_context
def set_password(ctx, account):
    """Set password protection for stored keys."""
    cfg, ks, state = _get_config_and_keystore(ctx)
    wxid = _resolve_account(cfg, account)

    if not wxid:
        if state.json_mode:
            print_json(error_envelope(
                "ACCOUNT_NOT_FOUND", "No account specified or discovered.",
                "Use --account or configure active_account.",
                command="key set-password",
            ))
        else:
            click.echo("Error: No account found. Use --account to specify.", err=True)
        ctx.exit(7)
        return

    try:
        # First retrieve the existing key (might need current password)
        current_password = None
        try:
            raw_key = ks.get_key("wechat", wxid)
        except KeyPasswordWrongError:
            current_password = click.prompt("Current password", hide_input=True)
            raw_key = ks.get_key("wechat", wxid, password=current_password)

        new_password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
        ks.store_key("wechat", wxid, raw_key, protection="password", password=new_password)

        if state.json_mode:
            print_json(success_envelope(
                {"account": wxid, "protection": "password"},
                command="key set-password",
            ))
        else:
            click.echo(f"Password protection enabled for {wxid}.")

    except KeyNotFoundError as e:
        if state.json_mode:
            print_json(error_envelope(e.code, e.message, e.remediation, command="key set-password"))
        else:
            click.echo(f"Error: {e.message}", err=True)
        ctx.exit(1)
    except KeyPasswordWrongError as e:
        if state.json_mode:
            print_json(error_envelope(e.code, e.message, e.remediation, command="key set-password"))
        else:
            click.echo(f"Error: {e.message}", err=True)
        ctx.exit(1)


@key.command(name="remove-password")
@click.option("--account", help="Target account wxid.")
@click.pass_context
def remove_password(ctx, account):
    """Remove password protection (revert to DPAPI)."""
    cfg, ks, state = _get_config_and_keystore(ctx)
    wxid = _resolve_account(cfg, account)

    if not wxid:
        if state.json_mode:
            print_json(error_envelope(
                "ACCOUNT_NOT_FOUND", "No account specified or discovered.",
                "Use --account or configure active_account.",
                command="key remove-password",
            ))
        else:
            click.echo("Error: No account found. Use --account to specify.", err=True)
        ctx.exit(7)
        return

    try:
        current_password = click.prompt("Current password", hide_input=True)
        raw_key = ks.get_key("wechat", wxid, password=current_password)

        if sys.platform != "win32":
            if state.json_mode:
                print_json(error_envelope(
                    "CONFIG_ERROR", "DPAPI only available on Windows.",
                    "Use password protection on non-Windows platforms.",
                    command="key remove-password",
                ))
            else:
                click.echo("Error: DPAPI only available on Windows.", err=True)
            ctx.exit(6)
            return

        ks.store_key("wechat", wxid, raw_key, protection="dpapi")

        if state.json_mode:
            print_json(success_envelope(
                {"account": wxid, "protection": "dpapi"},
                command="key remove-password",
            ))
        else:
            click.echo(f"Password protection removed for {wxid}. Now using DPAPI.")

    except KeyNotFoundError as e:
        if state.json_mode:
            print_json(error_envelope(e.code, e.message, e.remediation, command="key remove-password"))
        else:
            click.echo(f"Error: {e.message}", err=True)
        ctx.exit(1)
    except KeyPasswordWrongError as e:
        if state.json_mode:
            print_json(error_envelope(e.code, e.message, e.remediation, command="key remove-password"))
        else:
            click.echo(f"Error: {e.message}", err=True)
        ctx.exit(1)
