"""Query service — search and context retrieval.

Extracts business logic from the CLI query command so that it can be
reused by the GUI, API adapters, or tests without depending on Click.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from wxtools.core.schema import MessageFilter, QueryResult

logger = logging.getLogger("wxtools.services.query_service")


# ---------------------------------------------------------------------------
# Request DTOs
# ---------------------------------------------------------------------------

@dataclass
class QueryRequest:
    """Parameters for a message search."""

    keyword: Optional[str] = None
    contact: Optional[str] = None
    conversation: Optional[str] = None
    since: Optional[str] = None       # YYYY-MM-DD string
    until: Optional[str] = None       # YYYY-MM-DD string
    msg_type: Optional[str] = None
    limit: int = 100
    offset: int = 0
    surface: str = "chat"
    attachments: Optional[str] = None  # None | "path" | "check"
    sql: Optional[str] = None


@dataclass
class ContextRequest:
    """Parameters for fetching message context around a target message."""

    message_id: str
    window: int = 10  # messages before and after


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_since(value: Optional[str]) -> Optional[datetime]:
    """Parse a ``YYYY-MM-DD`` string into a UTC-aware datetime at 00:00:00."""
    if value is None:
        return None
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _parse_until(value: Optional[str]) -> Optional[datetime]:
    """Parse a ``YYYY-MM-DD`` string into a UTC-aware datetime at 23:59:59."""
    if value is None:
        return None
    return datetime.strptime(value, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, tzinfo=timezone.utc,
    )


def _build_filter(request: QueryRequest) -> MessageFilter:
    """Convert a :class:`QueryRequest` into a :class:`MessageFilter`."""
    return MessageFilter(
        keyword=request.keyword,
        contact=request.contact,
        conversation=request.conversation,
        since=_parse_since(request.since),
        until=_parse_until(request.until),
        msg_type=request.msg_type,
        limit=request.limit,
        offset=request.offset,
        surface=request.surface,
    )


def _merge_with_moments(
    reader,
    keyword: Optional[str],
    msg_filter: MessageFilter,
    limit: int,
    chat_result: QueryResult,
) -> QueryResult:
    """Merge chat results with Moments (SNS) results, best-effort."""
    try:
        from wxtools.plugins.wechat.sns_reader import SnsReader

        sns = SnsReader(reader._account_id, reader._cache_dir.parent)
        sns_result = sns.search(keyword=keyword, filters=msg_filter)
        all_msgs = chat_result.messages + sns_result.messages
        all_msgs.sort(key=lambda m: (m.timestamp, m.server_id))
        return QueryResult(
            messages=all_msgs[:limit],
            total_estimate=chat_result.total_estimate + sns_result.total_estimate,
            has_more=len(all_msgs) > limit,
            query=chat_result.query,
        )
    except Exception:
        logger.debug("SNS merge failed or sns.db unavailable, returning chat-only results")
        return chat_result


def _resolve_attachments(
    result: QueryResult,
    account_data_path: Path,
    mode: str,
) -> None:
    """Resolve (and optionally check) attachment paths on each message.

    Mutates ``msg.attachment_path`` and ``msg.attachment_exists`` in place.
    """
    from wxtools.plugins.wechat.attachment_resolver import AttachmentResolver

    resolver = AttachmentResolver(account_data_path)
    for msg in result.messages:
        msg.attachment_path = resolver.resolve_path(msg.type, msg.content)
        if mode == "check" and msg.attachment_path:
            msg.attachment_exists = resolver.check_exists(msg.attachment_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search(
    reader,
    account_data_path: Path,
    request: QueryRequest,
) -> QueryResult:
    """Execute a message search against the decrypted cache.

    Parameters
    ----------
    reader:
        An initialised ``DbReader`` instance.
    account_data_path:
        Path to the raw account data directory (used for attachment
        resolution).
    request:
        Search parameters wrapped in a :class:`QueryRequest`.

    Returns
    -------
    QueryResult
        Messages matching the query, with attachment info if requested.
    """
    msg_filter = _build_filter(request)
    keyword = request.keyword
    surface = request.surface
    limit = request.limit

    # --- surface routing ---------------------------------------------------
    if surface == "moments":
        from wxtools.plugins.wechat.sns_reader import SnsReader

        sns = SnsReader(reader._account_id, reader._cache_dir.parent)
        result = sns.search(keyword=keyword, filters=msg_filter)

    elif surface == "all":
        result = reader.search(keyword=keyword, filters=msg_filter)
        result = _merge_with_moments(reader, keyword, msg_filter, limit, result)

    else:
        # "chat" or "public" — handled uniformly by DbReader
        result = reader.search(keyword=keyword, filters=msg_filter)

    # --- attachment resolution ---------------------------------------------
    if request.attachments and result.messages:
        _resolve_attachments(result, account_data_path, request.attachments)

    return result


def search_raw_sql(reader, sql: str) -> dict:
    """Execute a raw SQL query (debug / power-user mode).

    Parameters
    ----------
    reader:
        An initialised ``DbReader`` instance.
    sql:
        The raw SQL string to execute.

    Returns
    -------
    dict
        ``{"rows": [...], "count": int}``
    """
    rows = reader.query_sql(sql)
    return {"rows": rows, "count": len(rows)}


def get_context(reader, request: ContextRequest) -> dict:
    """Retrieve messages surrounding a target message (context window).

    Intended for the GUI context drawer: given a message ID, return the
    target message plus *window* messages before and after it in the same
    conversation.

    The ``message_id`` is a composite string produced by
    ``schema_mapper.row_to_message`` in the form ``"<db_stem>:<local_id>"``,
    e.g. ``"message_0:12345"``.  We parse it to locate the correct shard DB
    and then scan all ``Msg_*`` / ``MSG`` tables in that shard.

    Parameters
    ----------
    reader:
        An initialised ``DbReader`` instance.
    request:
        Context parameters wrapped in a :class:`ContextRequest`.

    Returns
    -------
    dict
        ``{"target": <msg_dict | None>, "before": [...], "after": [...]}``
    """
    window = request.window
    message_id = request.message_id

    # ---- Parse composite ID -------------------------------------------------
    # Format: "<db_stem>:<local_id>"  e.g. "message_0:42"
    if ":" in message_id:
        db_stem, local_id_str = message_id.split(":", 1)
    else:
        # Fallback: treat the whole thing as a local_id, guess first shard
        db_stem = "message_0"
        local_id_str = message_id

    db_name = f"message/{db_stem}.db"

    # ---- Discover tables in the shard ---------------------------------------
    try:
        table_rows = reader.query_sql(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND (name LIKE 'Msg_%' OR name = 'MSG')",
            db_name=db_name,
        )
    except Exception:
        logger.debug("Could not list tables in %s", db_name)
        return {"target": None, "before": [], "after": []}

    tables = [r["name"] for r in table_rows]
    if not tables:
        return {"target": None, "before": [], "after": []}

    # ---- Detect schema version (4.x vs 3.x) --------------------------------
    is_v4 = any(t.startswith("Msg_") for t in tables)
    col_local_id = "local_id" if is_v4 else "localId"
    col_server_id = "server_id" if is_v4 else "MsgSvrID"
    col_time = "create_time" if is_v4 else "CreateTime"

    # ---- Find the target message across all tables --------------------------
    target = None
    target_table = None

    for table in tables:
        try:
            rows = reader.query_sql(
                f"SELECT *, '{table}' AS _src_table FROM [{table}] "
                f"WHERE {col_local_id} = {local_id_str} "
                f"OR {col_server_id} = {local_id_str} LIMIT 1",
                db_name=db_name,
            )
        except Exception:
            continue
        if rows:
            target = rows[0]
            target_table = table
            break

    if not target:
        return {"target": None, "before": [], "after": []}

    create_time = target.get(col_time, 0)

    # ---- Fetch surrounding messages from the same table ---------------------
    try:
        before_rows = reader.query_sql(
            f"SELECT * FROM [{target_table}] "
            f"WHERE {col_time} < {create_time} "
            f"ORDER BY {col_time} DESC LIMIT {window}",
            db_name=db_name,
        )
    except Exception:
        before_rows = []

    try:
        after_rows = reader.query_sql(
            f"SELECT * FROM [{target_table}] "
            f"WHERE {col_time} > {create_time} "
            f"ORDER BY {col_time} ASC LIMIT {window}",
            db_name=db_name,
        )
    except Exception:
        after_rows = []

    # Return chronological order for *before*
    before_rows = list(reversed(before_rows)) if before_rows else []

    # ---- Convert raw rows to Message dicts via schema_mapper ----------------
    try:
        from wxtools.plugins.wechat.schema_mapper import row_to_message

        def _row_to_dict(row: dict, db_stem: str, table: str) -> dict:
            """Best-effort conversion of a raw DB row to a Message dict."""
            try:
                msg = row_to_message(
                    row,
                    db_name=f"{db_stem}.db",
                    conversation_id=table,
                    conversation_title="",
                    sender_name="",
                    surface="chat",
                )
                return msg.to_dict()
            except Exception:
                # Fallback: return the raw row as-is
                return row

        target_dict = _row_to_dict(target, db_stem, target_table)
        before_dicts = [_row_to_dict(r, db_stem, target_table) for r in before_rows]
        after_dicts = [_row_to_dict(r, db_stem, target_table) for r in after_rows]
    except ImportError:
        # schema_mapper not available — return raw rows
        target_dict = target
        before_dicts = before_rows
        after_dicts = after_rows

    return {
        "target": target_dict,
        "before": before_dicts,
        "after": after_dicts,
    }
