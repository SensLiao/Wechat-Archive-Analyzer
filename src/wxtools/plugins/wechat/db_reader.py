"""Cross-shard message query and contact resolution."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from wxtools.core.errors import CacheEmptyError, NoResultsError, SqlError
from wxtools.core.schema import Contact, Message, MessageFilter, QueryResult
from wxtools.plugins.wechat.schema_mapper import row_to_contact, row_to_message


class DbReader:
    def __init__(self, account_id: str, cache_base: Union[str, Path]):
        self._account_id = account_id
        self._cache_dir = Path(cache_base) / account_id
        self._contacts_cache: Optional[Dict[str, Contact]] = None

    def _ensure_cache_exists(self) -> None:
        if not self._cache_dir.is_dir():
            raise CacheEmptyError()
        micromsg = self._cache_dir / "MicroMsg.db"
        if not micromsg.exists():
            raise CacheEmptyError()

    def _msg_shards(self) -> List[Path]:
        return sorted(self._cache_dir.glob("MSG*.db"))

    def _connect(self, db_path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_contacts(self) -> Dict[str, Contact]:
        if self._contacts_cache is not None:
            return self._contacts_cache
        micromsg = self._cache_dir / "MicroMsg.db"
        contacts: Dict[str, Contact] = {}
        if micromsg.exists():
            conn = self._connect(micromsg)
            try:
                for row in conn.execute("SELECT UserName, NickName, Alias, Remark FROM Contact"):
                    c = row_to_contact(dict(row))
                    contacts[c.id] = c
            finally:
                conn.close()
        self._contacts_cache = contacts
        return contacts

    def resolve_contact(self, wxid: str) -> Optional[Contact]:
        contacts = self._load_contacts()
        return contacts.get(wxid)

    def search(
        self,
        keyword: Optional[str] = None,
        filters: Optional[MessageFilter] = None,
    ) -> QueryResult:
        self._ensure_cache_exists()
        if filters is None:
            filters = MessageFilter()

        contacts = self._load_contacts()
        all_messages: List[Message] = []

        for shard in self._msg_shards():
            conn = self._connect(shard)
            try:
                where_clauses: List[str] = []
                params: List[Any] = []

                if keyword or filters.keyword:
                    kw = keyword or filters.keyword
                    where_clauses.append("StrContent LIKE ?")
                    params.append(f"%{kw}%")
                if filters.contact:
                    matched = [
                        c for c in contacts.values()
                        if filters.contact in (c.remark or c.nickname or c.id or "")
                    ]
                    if matched:
                        wxids = [c.id for c in matched]
                        placeholders = ",".join("?" * len(wxids))
                        where_clauses.append(f"StrTalker IN ({placeholders})")
                        params.extend(wxids)
                if filters.conversation:
                    where_clauses.append("StrTalker LIKE ?")
                    params.append(f"%{filters.conversation}%")
                if filters.since:
                    ts = int(filters.since.timestamp())
                    where_clauses.append("CreateTime >= ?")
                    params.append(ts)
                if filters.until:
                    ts = int(filters.until.timestamp())
                    where_clauses.append("CreateTime <= ?")
                    params.append(ts)
                if filters.msg_type:
                    type_codes = _type_name_to_codes(filters.msg_type)
                    if type_codes:
                        placeholders = ",".join("?" * len(type_codes))
                        where_clauses.append(f"Type IN ({placeholders})")
                        params.extend(type_codes)

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                sql = f"SELECT * FROM MSG WHERE {where_sql} ORDER BY CreateTime ASC, MsgSvrID ASC"

                for row in conn.execute(sql, params):
                    row_dict = dict(row)
                    talker = row_dict.get("StrTalker", "")
                    contact = contacts.get(talker)
                    sender_name = contact.display_name if contact else talker
                    conv_title = sender_name

                    msg = row_to_message(
                        row_dict,
                        db_name=shard.name,
                        sender_name=sender_name,
                        conversation_title=conv_title,
                    )
                    all_messages.append(msg)
            finally:
                conn.close()

        seen: Set[int] = set()
        unique: List[Message] = []
        for msg in all_messages:
            if msg.server_id not in seen:
                seen.add(msg.server_id)
                unique.append(msg)

        unique.sort(key=lambda m: (m.timestamp, m.server_id))

        total = len(unique)
        offset = filters.offset
        limit = filters.limit
        page = unique[offset: offset + limit]
        has_more = (offset + limit) < total

        return QueryResult(
            messages=page,
            total_estimate=total,
            has_more=has_more,
            query={
                "keyword": keyword or filters.keyword,
                "contact": filters.contact,
                "limit": limit,
                "offset": offset,
            },
        )

    def query_sql(self, sql: str, db_name: str = "MSG0.db") -> List[Dict[str, Any]]:
        self._ensure_cache_exists()
        sql_stripped = sql.strip().upper()
        if not sql_stripped.startswith("SELECT"):
            raise SqlError("Only SELECT statements are allowed")
        db_path = self._cache_dir / db_name
        if not db_path.exists():
            raise SqlError(f"Database not found: {db_name}")
        conn = self._connect(db_path)
        try:
            rows = conn.execute(sql).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise SqlError(str(e))
        finally:
            conn.close()


def _type_name_to_codes(type_name: str) -> List[int]:
    mapping: Dict[str, List[int]] = {
        "text": [1],
        "image": [3],
        "voice": [34],
        "video": [43],
        "file": [49],
        "system": [10000, 10002],
    }
    return mapping.get(type_name.lower(), [])
