"""Query command — thin CLI adapter over application.query_service."""

from __future__ import annotations

import json
import logging

import click

from wxtools.interfaces.cli.output import error_envelope, print_json, success_envelope
from wxtools.runtime.config import load_config
from wxtools.domain.errors import WxToolsError

logger = logging.getLogger("wxtools.interfaces.cli.query")


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
@click.option("--surface", type=click.Choice(["chat", "public", "moments", "all"], case_sensitive=False),
              default="chat", help="Data surface: chat, public (公众号), moments (朋友圈), or all.")
@click.option("--attachments", type=click.Choice(["path", "check"]),
              default=None, help="Attachment handling: path=resolve paths, check=verify existence.")
@click.option("--password", default=None, help="Password for key decryption.")
@click.pass_context
def query(ctx, keyword, contact, conversation, since, until_date, msg_type, limit, offset, sql, account, surface, attachments, password):
    """Search messages in decrypted WeChat databases."""
    from wxtools.application.account_service import resolve_account_and_reader
    from wxtools.application.query_service import QueryRequest, search, search_raw_sql

    state = ctx.obj
    cfg = load_config()

    if limit is None:
        limit = cfg.get("default_limit", 100)

    try:
        reader, account_data_path = resolve_account_and_reader(cfg, account, password=password)

        if sql:
            # Raw SQL mode
            data = search_raw_sql(reader, sql)
            if state.json_mode:
                print_json(success_envelope(data, command="query"))
            else:
                for row in data["rows"]:
                    click.echo(json.dumps(row, ensure_ascii=False, default=str))
            return

        request = QueryRequest(
            keyword=keyword,
            contact=contact,
            conversation=conversation,
            since=since,
            until=until_date,
            msg_type=msg_type,
            limit=limit,
            offset=offset,
            surface=surface,
            attachments=attachments,
        )

        result = search(reader, account_data_path, request)

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
