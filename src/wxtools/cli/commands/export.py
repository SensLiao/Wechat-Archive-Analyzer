"""Export command."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from wxtools.cli.exporters.csv_writer import CsvWriter
from wxtools.cli.exporters.html_writer import HtmlWriter
from wxtools.cli.exporters.json_writer import JsonWriter
from wxtools.cli.output import error_envelope, print_json, success_envelope
from wxtools.core.config import load_config
from wxtools.core.errors import ExportConfirmRequiredError, WxToolsError
from wxtools.core.schema import MessageFilter

logger = logging.getLogger("wxtools.cli.export")

WRITERS = {"json": JsonWriter, "csv": CsvWriter, "html": HtmlWriter}


@click.command()
@click.option(
    "--format", "fmt",
    default="json",
    type=click.Choice(["json", "csv", "html"], case_sensitive=False),
    help="Output format.",
)
@click.option("--output", "-o", "output_path", help="Output file or directory.")
@click.option("--contact", help="Scope to contact.")
@click.option("--conversation", help="Scope to conversation/group.")
@click.option("--since", help="Start date (YYYY-MM-DD).")
@click.option("--until", "until_date", help="End date (YYYY-MM-DD).")
@click.option("--limit", type=int, help="Max messages.")
@click.option("--account", help="Select account.")
@click.option("--yes", is_flag=True, help="Skip confirmation for large exports.")
@click.pass_context
def export(ctx, fmt, output_path, contact, conversation, since, until_date, limit, account, yes):
    """Export messages to file."""
    state = ctx.obj
    cfg = load_config()

    try:
        from wxtools.cli.commands.query import _resolve_account_and_reader

        reader = _resolve_account_and_reader(cfg, account, json_mode=state.json_mode)

        # Parse date filters
        since_dt: Optional[datetime] = None
        until_dt: Optional[datetime] = None
        if since:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if until_date:
            until_dt = datetime.strptime(until_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )

        msg_filter = MessageFilter(
            contact=contact,
            conversation=conversation,
            since=since_dt,
            until=until_dt,
            limit=limit or 1000000,
            offset=0,
        )

        # Count for confirmation
        total = reader.count_messages(msg_filter)

        if total > 1000 and not yes:
            if state.json_mode:
                raise ExportConfirmRequiredError(total)
            else:
                click.confirm(f"About to export ~{total} messages. Continue?", abort=True)

        # Determine output directory
        if not output_path:
            output_path = "."
        out = Path(output_path)
        # If user gave a file path with an extension, use its parent as output dir
        if out.suffix:
            out = out.parent
        out.mkdir(parents=True, exist_ok=True)

        # Create writer and stream messages
        writer_cls = WRITERS[fmt.lower()]
        writer = writer_cls(out)

        written = 0
        for msg in reader.iter_messages(msg_filter):
            writer.write_message(msg)
            written += 1

        manifest = writer.finalize()

        if state.json_mode:
            print_json(success_envelope(
                {
                    "total_messages": manifest["total_messages"],
                    "total_conversations": manifest["total_conversations"],
                    "files": manifest.get("files", []),
                    "output": str(out),
                    "format": fmt,
                },
                command="export",
            ))
        else:
            click.echo(f"Exported {manifest['total_messages']} messages ({fmt}) to {out}")
            for f in manifest.get("files", []):
                click.echo(f"  {f['path']} ({f['message_count']} messages)")

    except WxToolsError as e:
        if state.json_mode:
            env = error_envelope(e.code, e.message, e.remediation, command="export")
            if hasattr(e, "candidates"):
                env["error"]["candidates"] = e.candidates
            if hasattr(e, "estimated_count"):
                env["error"]["estimated_count"] = e.estimated_count
            print_json(env)
        else:
            click.echo(f"Error: {e.message}", err=True)
            click.echo(f"  Fix: {e.remediation}", err=True)
        exit_map = {
            "KEY_NOT_FOUND": 1, "DB_NOT_FOUND": 3, "CACHE_EMPTY": 3,
            "ACCOUNT_NOT_FOUND": 7, "EXPORT_CONFIRM_REQUIRED": 8,
        }
        ctx.exit(exit_map.get(e.code, 1))
