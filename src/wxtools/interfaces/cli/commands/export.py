"""Export command — thin CLI adapter over application.export_service."""

from __future__ import annotations

import logging

import click

from wxtools.interfaces.cli.output import error_envelope, print_json, success_envelope
from wxtools.runtime.config import load_config
from wxtools.domain.errors import ExportConfirmRequiredError, WxToolsError

logger = logging.getLogger("wxtools.interfaces.cli.export")


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
@click.option("--surface", type=click.Choice(["chat", "public", "moments", "all"], case_sensitive=False),
              default="chat", help="Data surface: chat, public (公众号), moments (朋友��), or all.")
@click.option("--attachments", type=click.Choice(["path", "check", "copy"]),
              default=None, help="Attachment handling: path=resolve, check=verify, copy=copy to export dir.")
@click.option("--password", default=None, help="Password for key decryption.")
@click.pass_context
def export(ctx, fmt, output_path, contact, conversation, since, until_date, limit, account, yes, surface, attachments, password):
    """Export messages to file."""
    from wxtools.application.account_service import resolve_account_and_reader
    from wxtools.application.export_service import (
        CONFIRMATION_THRESHOLD,
        ExportRequest,
        estimate_count,
        run_export,
    )
    from wxtools.domain.schema import MessageFilter

    state = ctx.obj
    cfg = load_config()

    try:
        reader, account_data_path = resolve_account_and_reader(cfg, account, password=password)

        # Set up moments reader if needed
        sns_reader = None
        if surface in ("moments", "all"):
            try:
                from wxtools.infrastructure.wechat.sns_reader import SnsReader
                sns_reader = SnsReader(reader._account_id, reader._cache_dir.parent)
            except Exception:
                pass

        # Build filter for count estimation
        from wxtools.application.export_service import _build_filter
        request = ExportRequest(
            format=fmt,
            output_dir=output_path or ".",
            contact=contact,
            conversation=conversation,
            since=since,
            until=until_date,
            limit=limit,
            surface=surface,
            attachments=attachments,
        )
        msg_filter = _build_filter(request)

        # Count for confirmation
        total = estimate_count(reader, sns_reader, msg_filter, surface)

        if total > CONFIRMATION_THRESHOLD and not yes:
            if state.json_mode:
                raise ExportConfirmRequiredError(total)
            else:
                click.confirm(f"About to export ~{total} messages. Continue?", abort=True)

        result = run_export(reader, account_data_path, request, sns_reader=sns_reader)

        if state.json_mode:
            print_json(success_envelope(
                {
                    "total_messages": result.total_messages,
                    "total_conversations": result.total_conversations,
                    "files": result.files,
                    "output": result.output_dir,
                    "format": result.format,
                },
                command="export",
            ))
        else:
            click.echo(f"Exported {result.total_messages} messages ({result.format}) to {result.output_dir}")
            for f in result.files:
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
