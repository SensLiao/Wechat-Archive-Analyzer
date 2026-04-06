"""Cross-shard message query and contact resolution for WeChat 4.x."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union

from wxtools.domain.errors import CacheEmptyError, SqlError
from wxtools.domain.schema import Contact, Message, MessageFilter, QueryResult
from wxtools.infrastructure.wechat.schema_mapper import row_to_contact, row_to_message


class DbReader:
    def __init__(self, account_id: str, cache_base: Union[str, Path]):
        self._account_id = account_id
        self._cache_dir = Path(cache_base) / account_id
        self._contacts_cache: Optional[Dict[str, Contact]] = None
        self._name2id_cache: Dict[str, Dict[int, str]] = {}

    def _ensure_cache_exists(self) -> None:
        if not self._cache_dir.is_dir():
            raise CacheEmptyError()
        # Check for either 4.x or 3.x layout
        contact_db = self._cache_dir / "contact" / "contact.db"
        micromsg = self._cache_dir / "MicroMsg.db"
        if not contact_db.exists() and not micromsg.exists():
            raise CacheEmptyError()

    def _msg_shards(self, surface: str = "chat") -> List[Path]:
        """Find message DB shards for the given surface.

        surface: "chat" (regular messages), "public" (biz/official accounts),
                 "all" (both), or "moments" (empty — sns uses separate reader).
        """
        msg_dir = self._cache_dir / "message"
        shards: List[Path] = []

        if surface in ("chat", "all"):
            # WeChat 4.x: message/message_N.db
            if msg_dir.is_dir():
                shards.extend(sorted(msg_dir.glob("message_*.db")))
            else:
                # WeChat 3.x fallback
                shards.extend(sorted(self._cache_dir.glob("MSG*.db")))

        if surface in ("public", "all"):
            # WeChat 4.x: message/biz_message_N.db
            if msg_dir.is_dir():
                shards.extend(sorted(msg_dir.glob("biz_message_*.db")))

        return shards

    def _connect(self, db_path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_name2id(self, db_path: Path) -> Dict[int, str]:
        """Load Name2Id mapping (rowid -> username) from a message DB."""
        cache_key = str(db_path)
        if cache_key in self._name2id_cache:
            return self._name2id_cache[cache_key]

        mapping: Dict[int, str] = {}
        conn = self._connect(db_path)
        try:
            for row in conn.execute("SELECT rowid, user_name FROM Name2Id"):
                mapping[row["rowid"]] = row["user_name"]
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
        self._name2id_cache[cache_key] = mapping
        return mapping

    def _load_contacts(self) -> Dict[str, Contact]:
        if self._contacts_cache is not None:
            return self._contacts_cache

        contacts: Dict[str, Contact] = {}

        # WeChat 4.x
        contact_db = self._cache_dir / "contact" / "contact.db"
        if contact_db.exists():
            conn = self._connect(contact_db)
            try:
                for row in conn.execute(
                    "SELECT username, nick_name, alias, remark FROM contact"
                ):
                    c = row_to_contact(dict(row))
                    contacts[c.id] = c
            finally:
                conn.close()
        else:
            # WeChat 3.x fallback
            micromsg = self._cache_dir / "MicroMsg.db"
            if micromsg.exists():
                conn = self._connect(micromsg)
                try:
                    for row in conn.execute(
                        "SELECT UserName, NickName, Alias, Remark FROM Contact"
                    ):
                        c = row_to_contact(dict(row))
                        contacts[c.id] = c
                finally:
                    conn.close()

        self._contacts_cache = contacts
        return contacts

    def resolve_contact(self, wxid: str) -> Optional[Contact]:
        contacts = self._load_contacts()
        return contacts.get(wxid)

    def _get_msg_tables(self, conn: sqlite3.Connection) -> List[str]:
        """Get all message tables from a shard (4.x: Msg_<hash>, 3.x: MSG)."""
        # WeChat 4.x
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
        ).fetchall()
        tables = [r["name"] for r in rows]
        if tables:
            return tables
        # WeChat 3.x fallback
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'MSG'"
        ).fetchall()
        return [r["name"] for r in rows]

    def _conversation_wxid_to_table(self, wxid: str) -> str:
        """Convert a conversation wxid to its MSG_ table name."""
        h = hashlib.md5(wxid.encode()).hexdigest()
        return f"Msg_{h}"

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
        surface = getattr(filters, "surface", "chat")

        for shard in self._msg_shards(surface):
            name2id = self._load_name2id(shard)
            conn = self._connect(shard)
            try:
                # Determine which tables to query
                if filters.conversation:
                    # If conversation filter, only check matching tables
                    target_tables = self._find_conversation_tables(
                        conn, filters.conversation, contacts, name2id
                    )
                else:
                    target_tables = self._get_msg_tables(conn)

                for table_name in target_tables:
                    conv_wxid = self._table_to_conversation(table_name, name2id)

                    # Detect schema version from table name
                    is_v4 = table_name.startswith("Msg_")
                    col_content = "message_content" if is_v4 else "StrContent"
                    col_time = "create_time" if is_v4 else "CreateTime"
                    col_type = "local_type" if is_v4 else "Type"
                    col_sender = "real_sender_id" if is_v4 else "StrTalker"

                    where_clauses: List[str] = []
                    params: List[Any] = []

                    if keyword or filters.keyword:
                        kw = keyword or filters.keyword
                        where_clauses.append(f"{col_content} LIKE ?")
                        params.append(f"%{kw}%")

                    if filters.contact:
                        if is_v4:
                            matched_ids = self._resolve_contact_ids(
                                filters.contact, contacts, name2id
                            )
                            if matched_ids:
                                placeholders = ",".join("?" * len(matched_ids))
                                where_clauses.append(
                                    f"{col_sender} IN ({placeholders})"
                                )
                                params.extend(matched_ids)
                        else:
                            # 3.x: StrTalker is a wxid string
                            matched_wxids = [
                                c.id for c in contacts.values()
                                if filters.contact in (c.display_name or "")
                            ]
                            if matched_wxids:
                                placeholders = ",".join("?" * len(matched_wxids))
                                where_clauses.append(
                                    f"{col_sender} IN ({placeholders})"
                                )
                                params.extend(matched_wxids)

                    if filters.since:
                        ts = int(filters.since.timestamp())
                        where_clauses.append(f"{col_time} >= ?")
                        params.append(ts)
                    if filters.until:
                        ts = int(filters.until.timestamp())
                        where_clauses.append(f"{col_time} <= ?")
                        params.append(ts)
                    if filters.msg_type:
                        type_codes = _type_name_to_codes(filters.msg_type)
                        if type_codes:
                            placeholders = ",".join("?" * len(type_codes))
                            where_clauses.append(
                                f"{col_type} IN ({placeholders})"
                            )
                            params.extend(type_codes)

                    where_sql = (
                        " AND ".join(where_clauses) if where_clauses else "1=1"
                    )
                    sql = (
                        f'SELECT * FROM "{table_name}" '
                        f"WHERE {where_sql} ORDER BY {col_time} ASC"
                    )

                    try:
                        for row in conn.execute(sql, params):
                            row_dict = dict(row)

                            if is_v4:
                                sender_id = row_dict.get("real_sender_id", 0)
                                sender_wxid = name2id.get(sender_id, "")
                            else:
                                sender_wxid = row_dict.get("StrTalker", "")

                            sender_contact = contacts.get(sender_wxid)
                            sender_name = (
                                sender_contact.display_name
                                if sender_contact
                                else sender_wxid
                            )

                            conv_contact = contacts.get(conv_wxid)
                            conv_title = (
                                conv_contact.display_name
                                if conv_contact
                                else conv_wxid
                            )

                            msg = row_to_message(
                                row_dict,
                                db_name=shard.name,
                                sender_name=sender_name,
                                sender_wxid=sender_wxid,
                                conversation_id=conv_wxid,
                                conversation_title=conv_title,
                                surface=self._surface_for_shard(shard.name),
                            )
                            all_messages.append(msg)
                    except sqlite3.OperationalError:
                        continue
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
        page = unique[offset : offset + limit]
        has_more = (offset + limit) < total

        return QueryResult(
            messages=page,
            total_estimate=total,
            has_more=has_more,
            query={
                "keyword": keyword or filters.keyword,
                "contact": filters.contact,
                "conversation": filters.conversation,
                "limit": limit,
                "offset": offset,
            },
        )

    def _build_where_clauses(
        self,
        filters: MessageFilter,
        is_4x: bool,
        contacts: Optional[Dict[str, Contact]] = None,
        name2id: Optional[Dict[int, str]] = None,
        keyword: Optional[str] = None,
    ) -> Tuple[List[str], List[Any]]:
        """Build WHERE clause parts and params from filters.

        Returns (where_parts, params).
        """
        col_content = "message_content" if is_4x else "StrContent"
        col_time = "create_time" if is_4x else "CreateTime"
        col_type = "local_type" if is_4x else "Type"
        col_sender = "real_sender_id" if is_4x else "StrTalker"

        where_clauses: List[str] = []
        params: List[Any] = []

        kw = keyword or filters.keyword
        if kw:
            where_clauses.append(f"{col_content} LIKE ?")
            params.append(f"%{kw}%")

        if filters.contact and contacts is not None and name2id is not None:
            if is_4x:
                matched_ids = self._resolve_contact_ids(
                    filters.contact, contacts, name2id
                )
                if matched_ids:
                    placeholders = ",".join("?" * len(matched_ids))
                    where_clauses.append(f"{col_sender} IN ({placeholders})")
                    params.extend(matched_ids)
            else:
                matched_wxids = [
                    c.id for c in contacts.values()
                    if filters.contact in (c.display_name or "")
                ]
                if matched_wxids:
                    placeholders = ",".join("?" * len(matched_wxids))
                    where_clauses.append(f"{col_sender} IN ({placeholders})")
                    params.extend(matched_wxids)

        if filters.since:
            ts = int(filters.since.timestamp())
            where_clauses.append(f"{col_time} >= ?")
            params.append(ts)
        if filters.until:
            ts = int(filters.until.timestamp())
            where_clauses.append(f"{col_time} <= ?")
            params.append(ts)
        if filters.msg_type:
            type_codes = _type_name_to_codes(filters.msg_type)
            if type_codes:
                placeholders = ",".join("?" * len(type_codes))
                where_clauses.append(f"{col_type} IN ({placeholders})")
                params.extend(type_codes)

        return where_clauses, params

    @staticmethod
    def _surface_for_shard(shard_name: str) -> str:
        """Determine the surface based on the shard filename."""
        if shard_name.startswith("biz_message"):
            return "public"
        return "chat"

    def _iter_all_tables(
        self, filters: MessageFilter
    ) -> Generator[
        Tuple[sqlite3.Connection, str, bool, Dict[int, str], str], None, None
    ]:
        """Yield (conn, table_name, is_4x, name2id, db_name) for matching tables.

        Caller is responsible for closing connections when done.
        """
        surface = getattr(filters, "surface", "chat")
        contacts = self._load_contacts()
        for shard in self._msg_shards(surface):
            name2id = self._load_name2id(shard)
            conn = self._connect(shard)
            try:
                if filters.conversation:
                    target_tables = self._find_conversation_tables(
                        conn, filters.conversation, contacts, name2id
                    )
                else:
                    target_tables = self._get_msg_tables(conn)

                for table_name in target_tables:
                    is_v4 = table_name.startswith("Msg_")
                    yield conn, table_name, is_v4, name2id, shard.name
            finally:
                conn.close()

    def count_messages(self, filters: MessageFilter) -> int:
        """Count messages matching filters across all shards."""
        self._ensure_cache_exists()
        contacts = self._load_contacts()
        total = 0

        for conn, table_name, is_v4, name2id, db_name in self._iter_all_tables(filters):
            where_parts, params = self._build_where_clauses(
                filters, is_v4, contacts, name2id
            )
            where_sql = " AND ".join(where_parts) if where_parts else "1=1"
            sql = f'SELECT COUNT(*) FROM "{table_name}" WHERE {where_sql}'
            try:
                row = conn.execute(sql, params).fetchone()
                total += row[0]
            except sqlite3.OperationalError:
                continue

        return total

    def search_page(self, filters: MessageFilter) -> QueryResult:
        """Paginated search: count total, then fetch one page."""
        self._ensure_cache_exists()
        contacts = self._load_contacts()

        total = self.count_messages(filters)

        # Collect all matching messages (for cross-shard sort + dedup)
        all_messages: List[Message] = []
        for conn, table_name, is_v4, name2id, db_name in self._iter_all_tables(filters):
            conv_wxid = self._table_to_conversation(table_name, name2id)
            where_parts, params = self._build_where_clauses(
                filters, is_v4, contacts, name2id
            )
            col_time = "create_time" if is_v4 else "CreateTime"
            where_sql = " AND ".join(where_parts) if where_parts else "1=1"
            sql = (
                f'SELECT * FROM "{table_name}" '
                f"WHERE {where_sql} ORDER BY {col_time} ASC"
            )
            try:
                for row in conn.execute(sql, params):
                    row_dict = dict(row)
                    if is_v4:
                        sender_id = row_dict.get("real_sender_id", 0)
                        sender_wxid = name2id.get(sender_id, "")
                    else:
                        sender_wxid = row_dict.get("StrTalker", "")
                    sender_contact = contacts.get(sender_wxid)
                    sender_name = (
                        sender_contact.display_name if sender_contact else sender_wxid
                    )
                    conv_contact = contacts.get(conv_wxid)
                    conv_title = (
                        conv_contact.display_name if conv_contact else conv_wxid
                    )
                    msg = row_to_message(
                        row_dict,
                        db_name=db_name,
                        sender_name=sender_name,
                        sender_wxid=sender_wxid,
                        conversation_id=conv_wxid,
                        conversation_title=conv_title,
                        surface=self._surface_for_shard(db_name),
                    )
                    all_messages.append(msg)
            except sqlite3.OperationalError:
                continue

        # Dedup by server_id
        seen: Set[int] = set()
        unique: List[Message] = []
        for msg in all_messages:
            if msg.server_id not in seen:
                seen.add(msg.server_id)
                unique.append(msg)
        unique.sort(key=lambda m: (m.timestamp, m.server_id))

        offset = filters.offset
        limit = filters.limit
        page = unique[offset : offset + limit]
        has_more = (offset + limit) < total

        return QueryResult(
            messages=page,
            total_estimate=total,
            has_more=has_more,
            query={
                "keyword": filters.keyword,
                "contact": filters.contact,
                "conversation": filters.conversation,
                "limit": limit,
                "offset": offset,
            },
        )

    def iter_messages(
        self, filters: MessageFilter
    ) -> Generator[Message, None, None]:
        """Yield Message objects matching filters. Respects filters.limit."""
        self._ensure_cache_exists()
        contacts = self._load_contacts()

        # Collect all, dedup, sort, then yield
        all_messages: List[Message] = []
        for conn, table_name, is_v4, name2id, db_name in self._iter_all_tables(filters):
            conv_wxid = self._table_to_conversation(table_name, name2id)
            where_parts, params = self._build_where_clauses(
                filters, is_v4, contacts, name2id
            )
            col_time = "create_time" if is_v4 else "CreateTime"
            where_sql = " AND ".join(where_parts) if where_parts else "1=1"
            sql = (
                f'SELECT * FROM "{table_name}" '
                f"WHERE {where_sql} ORDER BY {col_time} ASC"
            )
            try:
                for row in conn.execute(sql, params):
                    row_dict = dict(row)
                    if is_v4:
                        sender_id = row_dict.get("real_sender_id", 0)
                        sender_wxid = name2id.get(sender_id, "")
                    else:
                        sender_wxid = row_dict.get("StrTalker", "")
                    sender_contact = contacts.get(sender_wxid)
                    sender_name = (
                        sender_contact.display_name if sender_contact else sender_wxid
                    )
                    conv_contact = contacts.get(conv_wxid)
                    conv_title = (
                        conv_contact.display_name if conv_contact else conv_wxid
                    )
                    msg = row_to_message(
                        row_dict,
                        db_name=db_name,
                        sender_name=sender_name,
                        sender_wxid=sender_wxid,
                        conversation_id=conv_wxid,
                        conversation_title=conv_title,
                        surface=self._surface_for_shard(db_name),
                    )
                    all_messages.append(msg)
            except sqlite3.OperationalError:
                continue

        # Dedup by server_id
        seen: Set[int] = set()
        unique: List[Message] = []
        for msg in all_messages:
            if msg.server_id not in seen:
                seen.add(msg.server_id)
                unique.append(msg)
        unique.sort(key=lambda m: (m.timestamp, m.server_id))

        limit = filters.limit
        count = 0
        for msg in unique:
            if limit and count >= limit:
                break
            yield msg
            count += 1

    def _find_conversation_tables(
        self,
        conn: sqlite3.Connection,
        conversation_filter: str,
        contacts: Dict[str, Contact],
        name2id: Dict[int, str],
    ) -> List[str]:
        """Find MSG_ tables matching a conversation filter."""
        all_tables = self._get_msg_tables(conn)
        # Try exact wxid match first
        exact_table = self._conversation_wxid_to_table(conversation_filter)
        if exact_table in all_tables:
            return [exact_table]

        # Try matching via contact names
        matched = []
        for wxid, contact in contacts.items():
            if conversation_filter.lower() in (contact.display_name or "").lower():
                table = self._conversation_wxid_to_table(wxid)
                if table in all_tables:
                    matched.append(table)

        return matched if matched else all_tables

    def _table_to_conversation(
        self, table_name: str, name2id: Dict[int, str]
    ) -> str:
        """Reverse-lookup: find conversation wxid from table hash."""
        table_hash = table_name.replace("Msg_", "")
        for _rowid, wxid in name2id.items():
            if hashlib.md5(wxid.encode()).hexdigest() == table_hash:
                return wxid
        return table_name

    def _resolve_contact_ids(
        self,
        contact_filter: str,
        contacts: Dict[str, Contact],
        name2id: Dict[int, str],
    ) -> List[int]:
        """Find Name2Id rowids matching a contact filter string."""
        matched_wxids = set()
        for wxid, contact in contacts.items():
            if contact_filter.lower() in (contact.display_name or "").lower():
                matched_wxids.add(wxid)
        if not matched_wxids:
            matched_wxids.add(contact_filter)

        result = []
        for rowid, wxid in name2id.items():
            if wxid in matched_wxids:
                result.append(rowid)
        return result

    def query_sql(self, sql: str, db_name: str = "message/message_0.db") -> List[Dict[str, Any]]:
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
    """Convert type name(s) to WeChat raw type codes.

    Supports comma-separated values, e.g. ``"text,image"`` returns ``[1, 3]``.
    """
    mapping: Dict[str, List[int]] = {
        "text": [1],
        "image": [3],
        "voice": [34],
        "video": [43],
        "file": [49],
        "link": [49],  # links are a subtype of type 49 in WeChat
        "system": [10000, 10002],
    }
    codes: List[int] = []
    for name in type_name.split(","):
        name = name.strip().lower()
        if name:
            codes.extend(mapping.get(name, []))
    # Deduplicate while preserving order
    seen: set[int] = set()
    result: List[int] = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result
