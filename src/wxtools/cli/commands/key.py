"""Key management commands."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

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
from wxtools.core.unlock_session import UnlockSession
from wxtools.plugins.wechat.key_validator import validate_key_for_account

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

    if sys.platform != "win32":
        msg = (
            "Key extraction from WeChat process memory is only supported on Windows.\n"
            "On this platform, use 'wxtools key set <hex-or-json>' to import a known key."
        )
        if state.json_mode:
            print_json(error_envelope(
                "PLATFORM_NOT_SUPPORTED", msg,
                "Use 'wxtools key set' to import an already-extracted key.",
                command="key extract",
            ))
        else:
            click.echo(f"Error: {msg}", err=True)
        ctx.exit(6)
        return

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
        config_protection = cfg.get("keystore_protection", "auto")
        is_first_time = not ks.has_key("wechat", wxid)
        password = None

        if config_protection != "auto":
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
                protection = "password-file"
            else:
                protection = "windows-dpapi"
        else:
            # JSON mode or re-extraction: keep platform default
            protection = "auto"

        ks.store_key(
            "wechat", wxid, key_data.encode("ascii"),
            backend_name=protection, password=password,
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


def _find_db_dir(cfg, wxid: str) -> Path | None:
    """Resolve the db_storage directory for a given wxid."""
    from wxtools.plugins.wechat.account_discovery import discover_accounts, find_wechat_data_dir

    data_dir = cfg.get("wechat_data_dir", "auto")
    if data_dir == "auto":
        data_dir = find_wechat_data_dir()
    if not data_dir:
        return None
    accounts = discover_accounts(data_dir)
    for acc in accounts:
        if acc["wxid"] == wxid:
            return Path(acc["db_dir"])
    # Fallback: try direct path from config
    if data_dir:
        candidate = Path(data_dir) / wxid / "db_storage"
        if candidate.is_dir():
            return candidate
    return None


@key.command()
@click.option("--account", help="Target account wxid.")
@click.pass_context
def verify(ctx, account):
    """Verify stored key against encrypted databases."""
    cfg, ks, state = _get_config_and_keystore(ctx)
    wxid = _resolve_account(cfg, account)

    if not wxid:
        if state.json_mode:
            print_json(error_envelope(
                "ACCOUNT_NOT_FOUND", "未指定或未发现账号。",
                "使用 --account 或配置 active_account。",
                command="key verify",
            ))
        else:
            click.echo("错误: 未找到账号。使用 --account 指定。", err=True)
        ctx.exit(7)
        return

    try:
        # Retrieve key (may need password)
        password = None
        try:
            raw_key = ks.get_key("wechat", wxid)
        except KeyPasswordWrongError:
            password = click.prompt("请输入密钥密码", hide_input=True)
            raw_key = ks.get_key("wechat", wxid, password=password)

        key_data = raw_key.decode("ascii")

        # Find DB directory
        db_dir_str = cfg.get("wechat_db_dir", None)
        if db_dir_str and db_dir_str != "auto":
            db_dir = Path(db_dir_str)
        else:
            db_dir = _find_db_dir(cfg, wxid)

        if not db_dir or not db_dir.is_dir():
            if state.json_mode:
                print_json(error_envelope(
                    "DB_DIR_NOT_FOUND", "未找到数据库目录。",
                    "请确认 WeChat 数据路径配置正确。",
                    command="key verify",
                ))
            else:
                click.echo("错误: 未找到数据库目录。", err=True)
            ctx.exit(1)
            return

        if not state.json_mode:
            click.echo("正在验证密钥...")

        result = validate_key_for_account(key_data, db_dir)

        # Update metadata
        now = datetime.now(timezone.utc).isoformat()
        ks.update_metadata("wechat", wxid, {"last_verified": now})

        if state.json_mode:
            print_json(success_envelope(
                {"account": wxid, **result},
                command="key verify",
            ))
        else:
            if result["failed"] == 0 and result["total"] > 0:
                click.echo(f"密钥验证成功 \u2713 ({result['passed']}/{result['total']} 数据库通过)")
            elif result["total"] == 0:
                click.echo("警告: 未找到可验证的数据库文件。")
            else:
                click.echo(f"密钥验证部分失败: {result['passed']}/{result['total']} 通过")
                for d in result.get("details", []):
                    if not d["ok"]:
                        click.echo(f"  失败: {d['path']}")

    except KeyNotFoundError as e:
        if state.json_mode:
            print_json(error_envelope(e.code, e.message, e.remediation, command="key verify"))
        else:
            click.echo(f"错误: {e.message}", err=True)
        ctx.exit(1)
    except KeyPasswordWrongError as e:
        if state.json_mode:
            print_json(error_envelope(e.code, e.message, e.remediation, command="key verify"))
        else:
            click.echo("错误: 密码错误。", err=True)
        ctx.exit(1)


@key.command("set")
@click.argument("key_input")
@click.option("--account", help="Target account wxid.")
@click.pass_context
def set_key(ctx, key_input, account):
    """Manually set a decryption key (64-char hex or JSON file path)."""
    cfg, ks, state = _get_config_and_keystore(ctx)
    wxid = _resolve_account(cfg, account)

    if not wxid:
        if state.json_mode:
            print_json(error_envelope(
                "ACCOUNT_NOT_FOUND", "未指定或未发现账号。",
                "使用 --account 或配置 active_account。",
                command="key set",
            ))
        else:
            click.echo("错误: 未找到账号。使用 --account 指定。", err=True)
        ctx.exit(7)
        return

    # Determine key data: 64-char hex string or JSON file path
    key_path = Path(key_input)
    if key_path.is_file():
        try:
            key_data = key_path.read_text(encoding="utf-8").strip()
            # Validate it's JSON
            json.loads(key_data)
        except (json.JSONDecodeError, OSError) as e:
            if state.json_mode:
                print_json(error_envelope(
                    "INVALID_KEY_FORMAT", f"无法读取密钥文件: {e}",
                    "请提供有效的 JSON 密钥文件。",
                    command="key set",
                ))
            else:
                click.echo(f"错误: 无法读取密钥文件: {e}", err=True)
            ctx.exit(1)
            return
    else:
        # Validate hex string
        if not re.match(r"^[0-9a-fA-F]{64}$", key_input):
            if state.json_mode:
                print_json(error_envelope(
                    "INVALID_KEY_FORMAT", "密钥必须是64位十六进制字符串或有效的JSON文件路径。",
                    "请提供64位hex字符串或JSON文件。",
                    command="key set",
                ))
            else:
                click.echo("错误: 密钥必须是64位十六进制字符串或有效的JSON文件路径。", err=True)
            ctx.exit(1)
            return
        key_data = key_input

    # Find DB directory for validation
    db_dir_str = cfg.get("wechat_db_dir", None)
    if db_dir_str and db_dir_str != "auto":
        db_dir = Path(db_dir_str)
    else:
        db_dir = _find_db_dir(cfg, wxid)

    if not state.json_mode:
        click.echo("正在验证密钥...")

    if db_dir and db_dir.is_dir():
        result = validate_key_for_account(key_data, db_dir)
        if result["failed"] > 0:
            if not state.json_mode:
                click.echo(f"警告: 验证部分失败 ({result['passed']}/{result['total']} 通过)")
                for d in result.get("details", []):
                    if not d["ok"]:
                        click.echo(f"  失败: {d['path']}")
                if not click.confirm("是否仍然保存此密钥?"):
                    click.echo("已取消。")
                    ctx.exit(0)
                    return
            # In JSON mode, still store but report validation
    else:
        if not state.json_mode:
            click.echo("警告: 未找到数据库目录，跳过验证。")

    # Determine protection backend
    protection = "auto"
    password = None
    if not state.json_mode:
        config_protection = cfg.get("keystore_protection", "auto")
        if config_protection != "auto":
            protection = config_protection
        else:
            from wxtools.core.platform import get_default_backend_name
            default_backend = get_default_backend_name()
            if default_backend == "windows-dpapi":
                wants_password = click.confirm("是否使用密码保护密钥?", default=False)
                if wants_password:
                    password = click.prompt("设置密码", hide_input=True, confirmation_prompt=True)
                    protection = "password-file"
                else:
                    protection = "windows-dpapi"
            else:
                # Non-Windows: try system keychain, fallback to password
                from wxtools.core.secret_backends import get_backend
                try:
                    backend = get_backend(default_backend)
                    if backend.is_available():
                        protection = default_backend
                        click.echo(f"将使用 {default_backend} 保护密钥。")
                    else:
                        raise OSError("not available")
                except (OSError, Exception):
                    click.echo("系统密钥存储不可用，将使用密码保护。")
                    password = click.prompt("设置密码", hide_input=True, confirmation_prompt=True)
                    protection = "password-file"

    # Store key
    key_bytes = key_data.encode("ascii")
    try:
        ks.store_key("wechat", wxid, key_bytes,
                      backend_name=protection, password=password)

        if state.json_mode:
            print_json(success_envelope(
                {"account": wxid, "protection": protection, "status": "stored"},
                command="key set",
            ))
        else:
            click.echo(f"密钥已保存 \u2713 (账号: {wxid}, 保护方式: {protection})")

    except (OSError, ValueError) as e:
        if state.json_mode:
            print_json(error_envelope(
                "KEY_STORE_FAILED", str(e),
                "请检查权限和配置。",
                command="key set",
            ))
        else:
            click.echo(f"错误: {e}", err=True)
        ctx.exit(1)


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

        # TTL selection
        if not state.json_mode:
            click.echo("\n请选择密码有效时长（输入数字）：")
            click.echo("  1) 30分钟")
            click.echo("  2) 1小时")
            click.echo("  3) 2小时（推荐）")
            click.echo("  4) 24小时")
            ttl_choice = click.prompt("选择", type=int, default=3)
            ttl_map = {1: 30, 2: 60, 3: 120, 4: 1440}
            ttl_minutes = ttl_map.get(ttl_choice, 120)
        else:
            ttl_minutes = 120
        ks.update_metadata("wechat", wxid, {"session_ttl_minutes": ttl_minutes})

        if state.json_mode:
            print_json(success_envelope(
                {"account": wxid, "protection": "password", "session_ttl_minutes": ttl_minutes},
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
    """Remove password protection (revert to system secret backend)."""
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

        from wxtools.core.platform import get_default_backend_name
        from wxtools.core.secret_backends import get_backend as _get_backend
        default_backend = get_default_backend_name()
        try:
            backend = _get_backend(default_backend)
            if not backend.is_available() or default_backend == "password-file":
                raise OSError("no system backend")
        except (OSError, Exception):
            if state.json_mode:
                print_json(error_envelope(
                    "CONFIG_ERROR",
                    "No system secret backend available on this platform.",
                    "Password protection is required on this platform.",
                    command="key remove-password",
                ))
            else:
                click.echo("错误: 当前平台无系统密钥存储，无法移除密码保护。", err=True)
            ctx.exit(6)
            return

        ks.store_key("wechat", wxid, raw_key, backend_name=default_backend)

        if state.json_mode:
            print_json(success_envelope(
                {"account": wxid, "protection": default_backend},
                command="key remove-password",
            ))
        else:
            click.echo(f"Password protection removed for {wxid}. Now using {default_backend}.")

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


@key.command()
@click.option("--account", help="Target account wxid.")
@click.pass_context
def unlock(ctx, account):
    """Unlock key for session (cache decrypted key temporarily)."""
    cfg, ks, state = _get_config_and_keystore(ctx)
    wxid = _resolve_account(cfg, account)

    if not wxid:
        if state.json_mode:
            print_json(error_envelope(
                "ACCOUNT_NOT_FOUND", "未指定或未发现账号。",
                "使用 --account 或配置 active_account。",
                command="key unlock",
            ))
        else:
            click.echo("错误: 未找到账号。使用 --account 指定。", err=True)
        ctx.exit(7)
        return

    if not ks.has_key("wechat", wxid):
        if state.json_mode:
            print_json(error_envelope(
                "KEY_NOT_FOUND", f"未找到账号 {wxid} 的密钥。",
                "请先运行 wxtools key extract 提取密钥。",
                command="key unlock",
            ))
        else:
            click.echo(f"错误: 未找到账号 {wxid} 的密钥。请先运行 wxtools key extract。", err=True)
        ctx.exit(1)
        return

    session = UnlockSession(cfg.session_dir)

    # Check if already unlocked
    existing = session.get_key("wechat", wxid)
    if existing is not None:
        if state.json_mode:
            print_json(success_envelope(
                {"account": wxid, "status": "already_unlocked"},
                command="key unlock",
            ))
        else:
            click.echo("已处于登录状态，无需重复操作。")
        return

    try:
        # Try direct DPAPI first (no password needed)
        password = None
        try:
            raw_key = ks.get_key("wechat", wxid)
        except KeyPasswordWrongError:
            # Need password
            if state.json_mode:
                password = os.environ.get("WXTOOLS_PASSWORD")
                if not password:
                    print_json(error_envelope(
                        "KEY_PASSWORD_WRONG", "需要密码。",
                        "设置 WXTOOLS_PASSWORD 环境变量。",
                        command="key unlock",
                    ))
                    ctx.exit(1)
                    return
            else:
                password = click.prompt("请输入密码", hide_input=True)
            raw_key = ks.get_key("wechat", wxid, password=password)

        # Read TTL from metadata
        meta_path = ks._meta_path("wechat", wxid)
        ttl_minutes = 120
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text("utf-8"))
                ttl_minutes = meta.get("session_ttl_minutes", 120)
            except (json.JSONDecodeError, OSError):
                pass

        session.create("wechat", wxid, raw_key, ttl_minutes=ttl_minutes, password=password)

        hours = ttl_minutes / 60
        if state.json_mode:
            print_json(success_envelope(
                {"account": wxid, "status": "unlocked", "ttl_minutes": ttl_minutes},
                command="key unlock",
            ))
        else:
            if hours == int(hours):
                click.echo(f"已登录，{int(hours)}小时内无需重复输入密码。")
            else:
                click.echo(f"已登录，{ttl_minutes}分钟内无需重复输入密码。")

    except KeyNotFoundError as e:
        if state.json_mode:
            print_json(error_envelope(e.code, e.message, e.remediation, command="key unlock"))
        else:
            click.echo(f"错误: {e.message}", err=True)
        ctx.exit(1)
    except KeyPasswordWrongError as e:
        if state.json_mode:
            print_json(error_envelope(e.code, e.message, e.remediation, command="key unlock"))
        else:
            click.echo("错误: 密码错误。", err=True)
        ctx.exit(1)


@key.command()
@click.option("--account", help="Target account wxid.")
@click.option("--all", "clear_all", is_flag=True, help="Clear all sessions.")
@click.pass_context
def lock(ctx, account, clear_all):
    """Lock session (clear cached key)."""
    cfg, ks, state = _get_config_and_keystore(ctx)
    session = UnlockSession(cfg.session_dir)

    if clear_all:
        session.clear_all()
        if state.json_mode:
            print_json(success_envelope(
                {"status": "all_sessions_cleared"},
                command="key lock",
            ))
        else:
            click.echo("已退出所有登录。")
        return

    wxid = _resolve_account(cfg, account)
    if not wxid:
        if state.json_mode:
            print_json(error_envelope(
                "ACCOUNT_NOT_FOUND", "未指定或未发现账号。",
                "使用 --account 或 --all。",
                command="key lock",
            ))
        else:
            click.echo("错误: 未找到账号。使用 --account 指定或 --all 退出所有。", err=True)
        ctx.exit(7)
        return

    session.clear("wechat", wxid)
    if state.json_mode:
        print_json(success_envelope(
            {"account": wxid, "status": "locked"},
            command="key lock",
        ))
    else:
        click.echo("已退出登录。")
