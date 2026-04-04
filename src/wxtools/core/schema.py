"""Unified data models for wxtools."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class Message:
    id: str
    server_id: int
    conversation_id: str
    conversation_title: str
    sender_id: str
    sender_name: str
    is_self: bool
    timestamp: datetime
    type: str
    content: str
    raw_type: int
    raw_sub_type: int
    attachment_path: Optional[str]
    source_db: str
    attachment_exists: Optional[bool] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        if self.attachment_exists is None:
            d.pop("attachment_exists", None)
        return d


@dataclass
class Contact:
    id: str
    nickname: Optional[str] = None
    alias: Optional[str] = None
    remark: Optional[str] = None

    @property
    def display_name(self) -> str:
        return self.remark or self.nickname or self.alias or self.id

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.display_name, "remark": self.remark}


@dataclass
class Conversation:
    id: str
    title: str
    is_group: bool
    member_count: Optional[int] = None


@dataclass
class MessageFilter:
    keyword: Optional[str] = None
    contact: Optional[str] = None
    conversation: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    msg_type: Optional[str] = None
    limit: int = 100
    offset: int = 0
    sql: Optional[str] = None
    account: Optional[str] = None


@dataclass
class QueryResult:
    messages: List[Message]
    total_estimate: int
    has_more: bool
    query: dict = field(default_factory=dict)
