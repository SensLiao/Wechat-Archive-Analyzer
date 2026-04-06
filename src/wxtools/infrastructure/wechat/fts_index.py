"""FTS5 full-text search index for cached WeChat messages."""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("wxtools.fts_index")

# Regex matching CJK Unified Ideographs and common CJK blocks.
# Inserting spaces around each character lets the default FTS5 unicode61
# tokenizer treat every CJK character as an individual token, enabling
# substring-style search on Chinese text.
_CJK_RE = re.compile(r"([\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff])")


def _tokenize_cjk(text: str) -> str:
    """Space-separate CJK characters so FTS5 can index them individually."""
    if not text:
        return ""
    return _CJK_RE.sub(r" \1 ", text)


class FtsIndex:
    """Build and query an FTS5 index over cached message databases."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)
        self._index_path = self._cache_dir / "fts_index.db"

    def has_index(self) -> bool:
        """Check whether the FTS index file exists."""
        return self._index_path.exists()

    def build(self) -> Dict[str, Any]:
        """Create FTS5 virtual table and index all cached messages.

        Scans message DBs in the cache directory, supporting both
        WeChat 4.x (Msg_* tables with message_content) and
        3.x (MSG table with StrContent) schemas.

        Returns dict with ``{"indexed": count}``.
        """
        conn = sqlite3.connect(str(self._index_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5("
            "sender, content, db_path, local_id, server_id, create_time UNINDEXED"
            ")"
        )
        total = 0

        for db_path in self._iter_message_dbs():
            total += self._index_db(conn, db_path)

        conn.commit()
        conn.close()
        logger.info("FTS index built: %d messages indexed", total)
        return {"indexed": total}

    def search(self, keyword: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Search indexed messages using FTS5 MATCH.

        Returns list of dicts with keys: sender, content, db_path,
        local_id, server_id, create_time.
        """
        if not self.has_index():
            return []

        conn = sqlite3.connect(str(self._index_path))
        try:
            cur = conn.execute(
                "SELECT sender, content, db_path, local_id, server_id, create_time "
                "FROM messages_fts WHERE messages_fts MATCH ? LIMIT ?",
                (_tokenize_cjk(keyword), limit),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def drop(self) -> None:
        """Delete the FTS index file."""
        if self._index_path.exists():
            self._index_path.unlink()
            logger.info("FTS index dropped: %s", self._index_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_message_dbs(self) -> List[Path]:
        """Find all message DB shards in the cache directory."""
        msg_dir = self._cache_dir / "message"
        if msg_dir.is_dir():
            # WeChat 4.x: message_N.db + biz_message_N.db (exclude fts/resource)
            shards = [p for p in sorted(msg_dir.glob("message_[0-9]*.db"))]
            shards.extend(sorted(msg_dir.glob("biz_message_*.db")))
            return shards
        # WeChat 3.x fallback: MSG*.db in cache root
        return sorted(self._cache_dir.glob("MSG*.db"))

    def _index_db(self, fts_conn: sqlite3.Connection, db_path: Path) -> int:
        """Index all messages from a single DB file. Returns count indexed."""
        src = sqlite3.connect(str(db_path))
        count = 0
        try:
            tables = [
                r[0]
                for r in src.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]

            # 4.x schema: Name2Id table + Msg_<hash> tables
            if "Name2Id" in tables:
                count += self._index_4x(fts_conn, src, db_path, tables)
            # 3.x schema: MSG table with StrContent
            elif "MSG" in tables:
                count += self._index_3x(fts_conn, src, db_path)
        finally:
            src.close()
        return count

    def _index_4x(
        self,
        fts_conn: sqlite3.Connection,
        src: sqlite3.Connection,
        db_path: Path,
        tables: List[str],
    ) -> int:
        """Index WeChat 4.x Msg_* tables."""
        # Build Name2Id lookup: integer id -> wxid string
        name2id: Dict[int, str] = {}
        if "Name2Id" in tables:
            try:
                for row in src.execute("SELECT UsrName, local_id FROM Name2Id").fetchall():
                    name2id[row[1]] = row[0]
            except sqlite3.OperationalError:
                pass

        count = 0
        msg_tables = [t for t in tables if t.startswith("Msg_")]
        for table in msg_tables:
            try:
                rows = src.execute(
                    f"SELECT local_id, server_id, real_sender_id, message_content, create_time "
                    f"FROM [{table}]"
                ).fetchall()
            except sqlite3.OperationalError:
                logger.debug("Skipping table %s: missing expected columns", table)
                continue

            for local_id, server_id, sender_id, content, ts in rows:
                # Skip blob/compressed content, only index text
                if not isinstance(content, str):
                    continue
                sender = name2id.get(sender_id, str(sender_id)) if sender_id else ""
                fts_conn.execute(
                    "INSERT INTO messages_fts(sender, content, db_path, local_id, server_id, create_time) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (sender, _tokenize_cjk(content), str(db_path), local_id, server_id, ts),
                )
                count += 1
        return count

    def _index_3x(
        self,
        fts_conn: sqlite3.Connection,
        src: sqlite3.Connection,
        db_path: Path,
    ) -> int:
        """Index WeChat 3.x MSG table."""
        count = 0
        try:
            rows = src.execute(
                "SELECT localId, MsgSvrID, StrTalker, StrContent, CreateTime FROM MSG"
            ).fetchall()
        except sqlite3.OperationalError:
            logger.debug("Skipping 3.x MSG table in %s: missing expected columns", db_path)
            return 0

        for local_id, server_id, sender, content, ts in rows:
            fts_conn.execute(
                "INSERT INTO messages_fts(sender, content, db_path, local_id, server_id, create_time) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sender or "", _tokenize_cjk(content or ""), str(db_path), local_id, server_id, ts),
            )
            count += 1
        return count
