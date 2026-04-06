"""Export service — export messages to various formats.

Business logic extracted from the CLI export command so it can be
reused by the Web API, GUI, or any other adapter without depending
on Click or interactive prompts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from wxtools.infrastructure.exporters.csv_writer import CsvWriter
from wxtools.infrastructure.exporters.html_writer import HtmlWriter
from wxtools.infrastructure.exporters.json_writer import JsonWriter
from wxtools.domain.schema import Message, MessageFilter

logger = logging.getLogger("wxtools.application.export")

WRITERS = {"json": JsonWriter, "csv": CsvWriter, "html": HtmlWriter}

CONFIRMATION_THRESHOLD = 1000


# ---------------------------------------------------------------------------
# Request / Result DTOs
# ---------------------------------------------------------------------------

@dataclass
class ExportRequest:
    """Parameters for an export job."""

    format: str = "json"  # json, csv, html
    output_dir: str = "."
    contact: Optional[str] = None
    conversation: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: Optional[int] = None
    surface: str = "chat"
    attachments: Optional[str] = None  # None, "path", "check", "copy"
    template: Optional[str] = None  # V5: export template name


@dataclass
class ExportResult:
    """Result of an export operation."""

    total_messages: int
    total_conversations: int
    files: list = field(default_factory=list)
    output_dir: str = ""
    format: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_date(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    """Parse ``YYYY-MM-DD`` into a timezone-aware datetime.

    When *end_of_day* is True the time is set to 23:59:59 so the date
    is treated as an inclusive upper bound.
    """
    if value is None:
        return None
    dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt


def _build_filter(request: ExportRequest) -> MessageFilter:
    """Translate an :class:`ExportRequest` into a :class:`MessageFilter`."""
    return MessageFilter(
        contact=request.contact,
        conversation=request.conversation,
        since=_parse_date(request.since),
        until=_parse_date(request.until, end_of_day=True),
        limit=request.limit or 1_000_000,
        offset=0,
        surface=request.surface,
    )


def _resolve_output_dir(raw: str) -> Path:
    """Return a directory path, creating it if necessary.

    If *raw* looks like a file (has an extension), the parent directory is
    used instead.
    """
    out = Path(raw)
    if out.suffix:
        out = out.parent
    out.mkdir(parents=True, exist_ok=True)
    return out


def _iter_messages(
    reader,
    sns_reader,
    msg_filter: MessageFilter,
    surface: str,
) -> Iterator[Message]:
    """Yield messages from the appropriate readers based on *surface*."""
    if surface in ("chat", "public", "all"):
        yield from reader.iter_messages(msg_filter)
    if surface in ("moments", "all") and sns_reader is not None:
        yield from sns_reader.iter_messages(msg_filter)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def estimate_count(
    reader,
    sns_reader,
    msg_filter: MessageFilter,
    surface: str,
) -> int:
    """Return the estimated message count **without** exporting anything.

    The caller can compare the result against :data:`CONFIRMATION_THRESHOLD`
    and decide whether to prompt the user for confirmation.
    """
    if surface == "moments" and sns_reader is not None:
        return sns_reader.count_messages(msg_filter)

    if surface == "all" and sns_reader is not None:
        return reader.count_messages(msg_filter) + sns_reader.count_messages(msg_filter)

    return reader.count_messages(msg_filter)


def run_export(
    reader,
    account_data_path: Path,
    request: ExportRequest,
    sns_reader=None,
) -> ExportResult:
    """Execute a full export and return an :class:`ExportResult`.

    Parameters
    ----------
    reader:
        Primary chat reader (``WeChatReader`` or compatible).
    account_data_path:
        Root path to the account's data directory — used by the
        :class:`AttachmentResolver` when attachment handling is requested.
    request:
        All user-supplied export parameters.
    sns_reader:
        Optional moments reader (``SnsReader`` or compatible).

    Returns
    -------
    ExportResult
        Statistics and file listing for the completed export.
    """
    msg_filter = _build_filter(request)
    out = _resolve_output_dir(request.output_dir)

    fmt = request.format.lower()
    writer_cls = WRITERS.get(fmt)
    if writer_cls is None:
        raise ValueError(
            f"Unsupported export format '{request.format}'. "
            f"Choose from: {', '.join(sorted(WRITERS))}"
        )
    writer = writer_cls(out)

    # Attachment resolver (lazy import — only needed when attachments flag set)
    resolver = None
    if request.attachments is not None:
        from wxtools.infrastructure.wechat.attachment_resolver import AttachmentResolver

        resolver = AttachmentResolver(account_data_path)

    written = 0
    for msg in _iter_messages(reader, sns_reader, msg_filter, request.surface):
        if resolver is not None:
            _resolve_attachment(resolver, msg, request.attachments, out)
        writer.write_message(msg)
        written += 1

    manifest: dict = writer.finalize()

    logger.info(
        "Export complete: %d messages, %d conversations, format=%s, dir=%s",
        manifest["total_messages"],
        manifest["total_conversations"],
        fmt,
        out,
    )

    return ExportResult(
        total_messages=manifest["total_messages"],
        total_conversations=manifest["total_conversations"],
        files=manifest.get("files", []),
        output_dir=str(out),
        format=fmt,
    )


def _resolve_attachment(
    resolver,
    msg: Message,
    mode: Optional[str],
    output_dir: Path,
) -> None:
    """Mutate *msg* in-place with resolved attachment information.

    Modes:
    - ``"path"``: resolve the on-disk path only.
    - ``"check"``: resolve path and verify the file exists.
    - ``"copy"``: resolve, verify, and copy into the export directory.
    """
    msg.attachment_path = resolver.resolve_path(msg.type, msg.content)

    if mode in ("check", "copy") and msg.attachment_path:
        msg.attachment_exists = resolver.check_exists(msg.attachment_path)

    if mode == "copy" and msg.attachment_path:
        copied_name = resolver.copy_to_export(msg.attachment_path, output_dir)
        if copied_name:
            msg.attachment_path = f"attachments/{copied_name}"
