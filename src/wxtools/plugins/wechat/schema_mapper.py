"""Map WeChat DB rows to unified schema models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from wxtools.core.schema import Contact, Message

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
    sender_wxid: str = "",
    conversation_id: str = "",
    conversation_title: str = "",
    surface: str = "chat",
) -> Message:
    # WeChat 4.x uses local_type; 3.x uses Type
    raw_type = row.get("local_type", row.get("Type", 0))
    # Handle combined type values (e.g., 21474836529 = high bits + low bits)
    if raw_type > 0xFFFF:
        raw_sub_type = (raw_type >> 16) & 0xFFFF
        raw_type = raw_type & 0xFFFF
    else:
        raw_sub_type = row.get("SubType", 0)
    msg_type = map_message_type(raw_type, raw_sub_type)

    # WeChat 4.x uses message_content; 3.x uses StrContent
    content = row.get("message_content", row.get("StrContent", ""))
    if isinstance(content, bytes):
        content = ""  # Compressed content, skip for now
    content = content or ""

    display = row.get("DisplayContent", "") or ""
    if msg_type in ("system", "revoked") and display:
        content = display

    # WeChat 4.x uses create_time; 3.x uses CreateTime
    create_time = row.get("create_time", row.get("CreateTime", 0))
    ts = (
        datetime.fromtimestamp(create_time, tz=timezone.utc)
        if create_time
        else datetime.now(timezone.utc)
    )

    # Determine if self-sent
    # WeChat 3.x: IsSender field; 4.x: empty sender_wxid
    is_self = bool(row.get("IsSender", 0)) if "IsSender" in row else (not sender_wxid)

    # Build unique ID
    local_id = row.get("local_id", row.get("localId", 0))
    server_id = row.get("server_id", row.get("MsgSvrID", 0))

    return Message(
        id=f"{db_name.replace('.db', '')}:{local_id}",
        server_id=server_id,
        conversation_id=conversation_id or row.get("StrTalker", ""),
        conversation_title=conversation_title,
        sender_id=sender_wxid or row.get("StrTalker", ""),
        sender_name=sender_name,
        is_self=is_self,
        timestamp=ts,
        type=msg_type,
        content=content,
        raw_type=raw_type,
        raw_sub_type=raw_sub_type,
        attachment_path=None,
        source_db=db_name,
        surface=surface,
    )


def row_to_contact(row: dict) -> Contact:
    # WeChat 4.x uses snake_case; 3.x uses CamelCase
    return Contact(
        id=row.get("username", row.get("UserName", "")),
        nickname=row.get("nick_name", row.get("NickName")),
        alias=row.get("alias", row.get("Alias")),
        remark=row.get("remark", row.get("Remark")),
    )
