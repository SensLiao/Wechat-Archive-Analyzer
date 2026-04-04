"""Export command."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import click

import wxtools
from wxtools.cli.output import error_envelope, print_json, success_envelope
from wxtools.core.config import load_config
from wxtools.core.errors import ExportConfirmRequiredError, WxToolsError
from wxtools.core.schema import Message, MessageFilter

logger = logging.getLogger("wxtools.cli.export")

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*]')


def _sanitize_filename(name: str, max_len: int = 200) -> str:
    """Sanitize filename for Windows compatibility."""
    safe = _ILLEGAL_CHARS.sub("_", name)
    if len(safe) > max_len:
        import hashlib
        h = hashlib.md5(name.encode()).hexdigest()[:8]
        safe = safe[:max_len] + "_" + h
    return safe or "unnamed"


def _write_export_file(filepath: Path, messages: List[Message], meta: dict) -> None:
    """Stream-write messages to a JSON export file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('{\n')
        f.write(f'  "meta": {json.dumps(meta, ensure_ascii=False, indent=2)},\n')
        f.write('  "messages": [\n')
        for i, msg in enumerate(messages):
            comma = "," if i < len(messages) - 1 else ""
            f.write(f'    {json.dumps(msg.to_dict(), ensure_ascii=False)}{comma}\n')
        f.write('  ]\n')
        f.write('}\n')


@click.command()
@click.option("--format", "fmt", default="json", help="Output format (v1: json only).")
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

    if fmt != "json":
        msg = f"Format '{fmt}' not supported in v1. Only 'json' is available."
        if state.json_mode:
            print_json(error_envelope("CONFIG_ERROR", msg, "Use --format json.", command="export"))
        else:
            click.echo(f"Error: {msg}", err=True)
        ctx.exit(6)
        return

    try:
        from wxtools.cli.commands.query import _resolve_account_and_reader

        reader = _resolve_account_and_reader(cfg, account)

        # Build filter for counting
        since_dt = None
        until_dt = None
        if since:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if until_date:
            until_dt = datetime.strptime(until_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )

        # First pass: estimate count with high limit
        est_filter = MessageFilter(
            contact=contact,
            conversation=conversation,
            since=since_dt,
            until=until_dt,
            limit=limit or 1000000,
            offset=0,
        )
        est_result = reader.search(filters=est_filter)
        total = est_result.total_estimate

        # Confirmation for large exports
        if total > 1000 and not yes:
            if state.json_mode:
                raise ExportConfirmRequiredError(total)
            else:
                click.confirm(f"About to export ~{total} messages. Continue?", abort=True)

        # Collect all messages
        export_filter = MessageFilter(
            contact=contact,
            conversation=conversation,
            since=since_dt,
            until=until_dt,
            limit=limit or 1000000,
            offset=0,
        )
        result = reader.search(filters=export_filter)
        messages = result.messages

        # Determine output path
        if not output_path:
            output_path = "."

        out = Path(output_path)

        # Group by conversation
        convos: dict[str, List[Message]] = {}
        for msg in messages:
            cid = msg.conversation_id
            convos.setdefault(cid, []).append(msg)

        account_wxid = reader._account_id
        exported_files = []
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()

        if len(convos) == 1:
            # Single conversation → single file
            cid, msgs = next(iter(convos.items()))
            title = msgs[0].conversation_title if msgs else cid
            filename = _sanitize_filename(f"{cid}_{title}") + ".json"
            if out.suffix == ".json":
                filepath = out
            else:
                filepath = out / filename

            meta = {
                "wxtools_version": wxtools.__version__,
                "exported_at": now_iso,
                "account": account_wxid,
                "filters": {
                    "contact": contact,
                    "conversation": conversation,
                    "since": since,
                    "until": until_date,
                    "limit": limit,
                },
                "total_messages": len(msgs),
                "conversations_included": 1,
            }
            _write_export_file(filepath, msgs, meta)
            exported_files.append({
                "path": str(filepath),
                "conversation_id": cid,
                "message_count": len(msgs),
            })
        else:
            # Multiple conversations → directory with manifest
            if out.suffix == ".json":
                out = out.parent
            out.mkdir(parents=True, exist_ok=True)
            convos_dir = out / "conversations"
            convos_dir.mkdir(exist_ok=True)

            for cid, msgs in sorted(convos.items()):
                title = msgs[0].conversation_title if msgs else cid
                filename = _sanitize_filename(f"{cid}_{title}") + ".json"
                filepath = convos_dir / filename

                # Deduplicate filename collisions
                counter = 1
                while filepath.exists():
                    filepath = convos_dir / f"{filepath.stem}_{counter}.json"
                    counter += 1

                meta = {
                    "wxtools_version": wxtools.__version__,
                    "exported_at": now_iso,
                    "account": account_wxid,
                    "filters": {"contact": contact, "conversation": conversation, "since": since, "until": until_date},
                    "total_messages": len(msgs),
                    "conversations_included": 1,
                }
                _write_export_file(filepath, msgs, meta)

                time_range = []
                if msgs:
                    time_range = [msgs[0].timestamp.isoformat(), msgs[-1].timestamp.isoformat()]

                exported_files.append({
                    "path": str(filepath.relative_to(out)),
                    "conversation_id": cid,
                    "message_count": len(msgs),
                    "time_range": time_range,
                })

            # Write manifest
            manifest = {
                "wxtools_version": wxtools.__version__,
                "exported_at": now_iso,
                "account": account_wxid,
                "export_root": str(out),
                "files": exported_files,
                "filters_applied": {"contact": contact, "conversation": conversation, "since": since, "until": until_date},
                "total_messages": len(messages),
                "total_files": len(exported_files),
            }
            manifest_path = out / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        if state.json_mode:
            print_json(success_envelope(
                {
                    "total_messages": len(messages),
                    "files": exported_files,
                    "output": str(out),
                },
                command="export",
            ))
        else:
            click.echo(f"Exported {len(messages)} messages to {out}")
            for ef in exported_files:
                click.echo(f"  {ef['path']} ({ef['message_count']} messages)")

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
