"""Query command."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import click

from wxtools.cli.output import error_envelope, print_json, success_envelope
from wxtools.core.config import load_config
from wxtools.core.errors import KeyNotFoundError, KeyPasswordWrongError, WxToolsError
from wxtools.core.keystore import Keystore
from wxtools.core.schema import MessageFilter
from wxtools.core.unlock_session import UnlockSession

logger = logging.getLogger("wxtools.cli.query")


def _get_key_with_session(cfg, ks: Keystore, wxid: str, json_mode: bool) -> bytes:
    """Retrieve key trying session, DPAPI, env var, then interactive prompt."""
    # 1. Try session
    session = UnlockSession(cfg.session_dir)
    session_key = session.get_key("wechat", wxid)
    if session_key is not None:
        return session_key

    # 2. Try direct DPAPI (no password)
    try:
        return ks.get_key("wechat", wxid)
    except KeyPasswordWrongError:
        pass

    # 3. Try env var
    env_password = os.environ.get("WXTOOLS_PASSWORD")
    if env_password:
        try:
            return ks.get_key("wechat", wxid, password=env_password)
        except KeyPasswordWrongError:
            pass

    # 4. Try interactive prompt (non-JSON mode only)
    if not json_mode:
        try:
            password = click.prompt("请输入密码", hide_input=True)
            return ks.get_key("wechat", wxid, password=password)
        except KeyPasswordWrongError:
            pass

    raise KeyNotFoundError(wxid)


def _resolve_account_and_reader(cfg, account_arg, json_mode: bool = False):
    """Resolve account, ensure cache exists (decrypt if needed), return DbReader."""
    from wxtools.plugins.wechat.account_discovery import discover_accounts, find_wechat_data_dir
    from wxtools.plugins.wechat.db_reader import DbReader
    from wxtools.plugins.wechat.decryptor import Decryptor

    # Resolve data dir
    data_dir = cfg.get("wechat_data_dir", "auto")
    if data_dir == "auto":
        data_dir = find_wechat_data_dir()
    if not data_dir:
        from wxtools.core.errors import DbNotFoundError
        raise DbNotFoundError("auto-detect failed")

    # Resolve account
    wxid = account_arg
    if not wxid:
        active = cfg.get("active_account", "auto")
        if active != "auto":
            wxid = active
        else:
            accounts = discover_accounts(data_dir)
            if not accounts:
                from wxtools.core.errors import AccountNotFoundError
                raise AccountNotFoundError("")
            wxid = accounts[0]["wxid"]

    # Find DB source directory
    accounts = discover_accounts(data_dir)
    db_dir = None
    for acc in accounts:
        if acc["wxid"] == wxid:
            db_dir = acc["db_dir"]
            break

    if not db_dir:
        from wxtools.core.errors import AccountNotFoundError
        raise AccountNotFoundError(wxid)

    # Ensure decrypted cache exists
    cache_dir = cfg.cache_dir
    account_cache = cache_dir / wxid
    ks = Keystore(cfg.keys_dir)

    from pathlib import Path

    # Always run decrypt_all — it checks mtime per file and only
    # re-decrypts databases whose source is newer than the cache.
    raw_key = _get_key_with_session(cfg, ks, wxid, json_mode)
    key_data = raw_key.decode("ascii")
    decryptor = Decryptor()
    decryptor.decrypt_all(Path(db_dir), account_cache, key_data)

    return DbReader(wxid, cache_dir)


@click.command()
@click.argument("keyword", required=False)
@click.option("--contact", help="Filter by contact name.")
@click.option("--conversation", help="Filter by conversation/group name.")
@click.option("--since", help="Start date (YYYY-MM-DD).")
@click.option("--until", "until_date", help="End date (YYYY-MM-DD).")
@click.option("--type", "msg_type", help="Message type filter.")
@click.option("--limit", type=int, default=None, help="Max results.")
@click.option("--offset", type=int, default=0, help="Pagination offset.")
@click.option("--sql", help="Raw SQL query (debug mode).")
@click.option("--account", help="Select account wxid.")
@click.pass_context
def query(ctx, keyword, contact, conversation, since, until_date, msg_type, limit, offset, sql, account):
    """Search messages in decrypted WeChat databases."""
    state = ctx.obj
    cfg = load_config()

    if limit is None:
        limit = cfg.get("default_limit", 100)

    try:
        reader = _resolve_account_and_reader(cfg, account, json_mode=state.json_mode)

        if sql:
            # Raw SQL mode
            rows = reader.query_sql(sql)
            if state.json_mode:
                print_json(success_envelope(
                    {"rows": rows, "count": len(rows)},
                    command="query",
                ))
            else:
                for row in rows:
                    click.echo(json.dumps(row, ensure_ascii=False, default=str))
            return

        # Build filter
        since_dt = None
        until_dt = None
        if since:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if until_date:
            until_dt = datetime.strptime(until_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )

        msg_filter = MessageFilter(
            keyword=keyword,
            contact=contact,
            conversation=conversation,
            since=since_dt,
            until=until_dt,
            msg_type=msg_type,
            limit=limit,
            offset=offset,
        )

        result = reader.search(keyword=keyword, filters=msg_filter)

        if state.json_mode:
            print_json(success_envelope(
                {
                    "messages": [m.to_dict() for m in result.messages],
                    "total_estimate": result.total_estimate,
                    "has_more": result.has_more,
                    "query": result.query,
                },
                command="query",
            ))
        else:
            if not result.messages:
                click.echo("No results found.")
            else:
                click.echo(f"Found ~{result.total_estimate} messages (showing {len(result.messages)}):\n")
                for msg in result.messages:
                    ts = msg.timestamp.strftime("%Y-%m-%d %H:%M")
                    prefix = "[self]" if msg.is_self else msg.sender_name
                    type_tag = f"[{msg.type}] " if msg.type != "text" else ""
                    click.echo(f"{prefix} ({ts}):")
                    click.echo(f"  {type_tag}{msg.content[:200]}")
                    click.echo()
                if result.has_more:
                    next_offset = offset + limit
                    click.echo(f"More results available. Use --offset {next_offset} to see next page.")

    except WxToolsError as e:
        if state.json_mode:
            print_json(error_envelope(e.code, e.message, e.remediation, command="query"))
        else:
            click.echo(f"Error: {e.message}", err=True)
            click.echo(f"  Fix: {e.remediation}", err=True)
        exit_map = {
            "KEY_NOT_FOUND": 1, "KEY_PASSWORD_WRONG": 1,
            "DB_NOT_FOUND": 3, "DB_LOCKED": 3, "DB_DECRYPT_FAILED": 3, "CACHE_EMPTY": 3,
            "AMBIGUOUS_CONTACT": 4, "AMBIGUOUS_CONVERSATION": 4,
            "SQL_ERROR": 5, "ACCOUNT_NOT_FOUND": 7,
        }
        ctx.exit(exit_map.get(e.code, 1))
