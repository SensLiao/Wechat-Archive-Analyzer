"""Map WeChat DB rows to unified schema models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from wxtools.core.schema import Message, Contact

_TYPE_MAP: Dict[Tuple[int, Optional[int]], str] = {
    (1, 0): "text",
    (3, 0): "image",
    (34, 0): "voice",
    (42, 0): "contact_card",
    (43, 0): "video",
    (47, 0): "emoticon",
    (48, 0): "location",
    (49, 1): "link",
    (49, 5): "link",
    (49, 6): "file",
    (49, 8): "gif",
    (49, 19): "chat_record",
    (49, 33): "mini_program",
    (49, 36): "mini_program",
    (49, 57): "quote_reply",
    (49, 2000): "transfer",
    (49, 2001): "red_packet",
    (10000, 0): "system",
    (10002, 0): "revoked",
}


def map_message_type(raw_type: int, raw_sub_type: int) -> str:
    result = _TYPE_MAP.get((raw_type, raw_sub_type))
    if result:
        return result
    result = _TYPE_MAP.get((raw_type, None))
    if result:
        return result
    if raw_type == 49:
        return "rich_media"
    return "unknown"


def row_to_message(
    row: dict,
    db_name: str,
    sender_name: str = "",
    conversation_title: str = "",
) -> Message:
    raw_type = row.get("Type", 0)
    raw_sub_type = row.get("SubType", 0)
    msg_type = map_message_type(raw_type, raw_sub_type)

    content = row.get("StrContent", "") or ""
    display = row.get("DisplayContent", "") or ""

    if msg_type in ("system", "revoked") and display:
        content = display

    create_time = row.get("CreateTime", 0)
    ts = datetime.fromtimestamp(create_time, tz=timezone.utc) if create_time else datetime.now(timezone.utc)

    return Message(
        id=f"{db_name.replace('.db', '')}:{row.get('localId', 0)}",
        server_id=row.get("MsgSvrID", 0),
        conversation_id=row.get("StrTalker", ""),
        conversation_title=conversation_title,
        sender_id=row.get("StrTalker", ""),
        sender_name=sender_name,
        is_self=bool(row.get("IsSender", 0)),
        timestamp=ts,
        type=msg_type,
        content=content,
        raw_type=raw_type,
        raw_sub_type=raw_sub_type,
        attachment_path=None,
        source_db=db_name,
    )


def row_to_contact(row: dict) -> Contact:
    return Contact(
        id=row.get("UserName", ""),
        nickname=row.get("NickName"),
        alias=row.get("Alias"),
        remark=row.get("Remark"),
    )
