"""Moments (朋友圈) reader for WeChat sns.db."""

from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union

from wxtools.core.errors import CacheEmptyError
from wxtools.core.schema import Contact, Message, MessageFilter, QueryResult


# SnsMessage_tmp3.type mapping
_SNS_MSG_TYPE_MAP = {
    1: "sns_like",
    2: "sns_comment",
    4: "sns_system",
}


def _parse_timeline_xml(xml_content: str) -> Optional[Dict[str, str]]:
    """Extract post metadata from SnsTimeLine XML content."""
    try:
        root = ET.fromstring(xml_content)
        tl = root.find("TimelineObject")
        if tl is None:
            return None
        return {
            "post_id": tl.findtext("id", ""),
            "username": tl.findtext("username", ""),
            "create_time": tl.findtext("createTime", "0"),
            "content_desc": tl.findtext("contentDesc", ""),
        }
    except ET.ParseError:
        return None


class SnsReader:
    """Read Moments data from the sns/sns.db cache."""

    def __init__(self, account_id: str, cache_base: Union[str, Path]):
        self._account_id = account_id
        self._cache_dir = Path(cache_base) / account_id
        self._contacts_cache: Optional[Dict[str, Contact]] = None

    def _sns_db_path(self) -> Path:
        return self._cache_dir / "sns" / "sns.db"

    def _ensure_exists(self) -> None:
        if not self._sns_db_path().exists():
            raise CacheEmptyError()

    def _connect(self, db_path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_contacts(self) -> Dict[str, Contact]:
        """Load contacts from contact DB for name resolution."""
        if self._contacts_cache is not None:
            return self._contacts_cache

        contacts: Dict[str, Contact] = {}
        contact_db = self._cache_dir / "contact" / "contact.db"
        if contact_db.exists():
            conn = self._connect(contact_db)
            try:
                for row in conn.execute(
                    "SELECT username, nick_name, alias, remark FROM contact"
                ):
                    from wxtools.plugins.wechat.schema_mapper import row_to_contact
                    c = row_to_contact(dict(row))
                    contacts[c.id] = c
            finally:
                conn.close()

        self._contacts_cache = contacts
        return contacts

    def _resolve_name(self, wxid: str) -> str:
        contacts = self._load_contacts()
        c = contacts.get(wxid)
        return c.display_name if c else wxid

    def _post_to_message(
        self, tid: int, username: str, xml_content: str, db_name: str = "sns.db"
    ) -> Optional[Message]:
        """Convert a SnsTimeLine row to a Message."""
        parsed = _parse_timeline_xml(xml_content) if xml_content else None
        if parsed is None:
            return None

        create_time = int(parsed["create_time"] or "0")
        ts = (
            datetime.fromtimestamp(create_time, tz=timezone.utc)
            if create_time
            else datetime.now(timezone.utc)
        )
        poster_name = self._resolve_name(username)
        content_desc = parsed["content_desc"] or ""
        post_id = parsed["post_id"] or str(tid)

        return Message(
            id=f"sns_post:{post_id}",
            server_id=abs(tid),
            conversation_id=f"sns:{post_id}",
            conversation_title=f"{poster_name} 的朋友圈",
            sender_id=username,
            sender_name=poster_name,
            is_self=False,
            timestamp=ts,
            type="sns_post",
            content=content_desc,
            raw_type=0,
            raw_sub_type=0,
            attachment_path=None,
            source_db=db_name,
            surface="moments",
        )

    def _comment_to_message(
        self, row: dict, db_name: str = "sns.db"
    ) -> Message:
        """Convert a SnsMessage_tmp3 row to a Message."""
        msg_type = _SNS_MSG_TYPE_MAP.get(row.get("type", 0), "sns_system")
        create_time = row.get("create_time", 0)
        ts = (
            datetime.fromtimestamp(create_time, tz=timezone.utc)
            if create_time
            else datetime.now(timezone.utc)
        )
        feed_id = row.get("feed_id", 0)
        from_user = row.get("from_username", "")
        from_nick = row.get("from_nickname", "") or self._resolve_name(from_user)
        content = row.get("content", "") or ""

        if msg_type == "sns_like":
            content = content or f"{from_nick} 赞了"

        return Message(
            id=f"sns_msg:{row.get('local_id', 0)}",
            server_id=abs(row.get("local_id", 0)),
            conversation_id=f"sns:{abs(feed_id)}",
            conversation_title="",
            sender_id=from_user,
            sender_name=from_nick,
            is_self=False,
            timestamp=ts,
            type=msg_type,
            content=content,
            raw_type=row.get("type", 0),
            raw_sub_type=0,
            attachment_path=None,
            source_db=db_name,
            surface="moments",
        )

    def search(
        self,
        keyword: Optional[str] = None,
        filters: Optional[MessageFilter] = None,
    ) -> QueryResult:
        """Search moments posts and comments."""
        self._ensure_exists()
        if filters is None:
            filters = MessageFilter(surface="moments")

        all_messages: List[Message] = []
        conn = self._connect(self._sns_db_path())

        try:
            # Query posts from SnsTimeLine
            all_messages.extend(self._query_posts(conn, keyword, filters))
            # Query comments from SnsMessage_tmp3
            all_messages.extend(self._query_comments(conn, keyword, filters))
        finally:
            conn.close()

        all_messages.sort(key=lambda m: (m.timestamp, m.server_id))

        total = len(all_messages)
        offset = filters.offset
        limit = filters.limit
        page = all_messages[offset : offset + limit]
        has_more = (offset + limit) < total

        return QueryResult(
            messages=page,
            total_estimate=total,
            has_more=has_more,
            query={
                "keyword": keyword or filters.keyword,
                "surface": "moments",
                "limit": limit,
                "offset": offset,
            },
        )

    def _query_posts(
        self, conn: sqlite3.Connection, keyword: Optional[str], filters: MessageFilter
    ) -> List[Message]:
        """Query SnsTimeLine for posts."""
        messages: List[Message] = []
        for row in conn.execute("SELECT tid, user_name, content FROM SnsTimeLine"):
            msg = self._post_to_message(
                row["tid"], row["user_name"], row["content"]
            )
            if msg is None:
                continue

            # Apply filters
            kw = keyword or filters.keyword
            if kw and kw.lower() not in msg.content.lower():
                continue
            if filters.since and msg.timestamp < filters.since:
                continue
            if filters.until and msg.timestamp > filters.until:
                continue
            if filters.contact:
                if filters.contact.lower() not in msg.sender_name.lower():
                    continue

            messages.append(msg)

        return messages

    def _query_comments(
        self, conn: sqlite3.Connection, keyword: Optional[str], filters: MessageFilter
    ) -> List[Message]:
        """Query SnsMessage_tmp3 for comments and likes."""
        messages: List[Message] = []
        try:
            for row in conn.execute(
                "SELECT local_id, create_time, type, feed_id, "
                "from_username, from_nickname, to_username, to_nickname, content "
                "FROM SnsMessage_tmp3"
            ):
                msg = self._comment_to_message(dict(row))

                kw = keyword or filters.keyword
                if kw and kw.lower() not in msg.content.lower():
                    continue
                if filters.since and msg.timestamp < filters.since:
                    continue
                if filters.until and msg.timestamp > filters.until:
                    continue

                messages.append(msg)
        except sqlite3.OperationalError:
            pass

        return messages

    def count_messages(self, filters: MessageFilter) -> int:
        """Count matching moments entries."""
        result = self.search(filters=filters)
        return result.total_estimate

    def iter_messages(
        self, filters: MessageFilter
    ) -> Generator[Message, None, None]:
        """Yield Message objects for moments data."""
        result = self.search(filters=MessageFilter(
            keyword=filters.keyword,
            contact=filters.contact,
            since=filters.since,
            until=filters.until,
            limit=filters.limit,
            offset=0,
            surface="moments",
        ))
        yield from result.messages
