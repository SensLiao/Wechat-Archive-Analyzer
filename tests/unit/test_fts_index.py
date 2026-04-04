"""Tests for FTS5 index build, query, and drop."""
import sqlite3
import hashlib
import pytest
from wxtools.plugins.wechat.fts_index import FtsIndex

@pytest.fixture
def cache_with_messages(tmp_path):
    cache_dir = tmp_path / "wxid_test"
    msg_dir = cache_dir / "message"
    msg_dir.mkdir(parents=True)
    conn = sqlite3.connect(msg_dir / "message_0.db")
    conn.execute("CREATE TABLE Name2Id (user_name TEXT)")
    conn.execute("INSERT INTO Name2Id VALUES ('friend1')")
    table_hash = hashlib.md5(b"friend1").hexdigest()
    table = f"Msg_{table_hash}"
    conn.execute(f"""CREATE TABLE {table} (
        local_id INTEGER PRIMARY KEY, server_id INTEGER, local_type INTEGER,
        sender_wxid TEXT, message_content TEXT, create_time INTEGER, display_content TEXT
    )""")
    for i in range(100):
        conn.execute(f"INSERT INTO {table} VALUES (?,?,1,'friend1',?,?,'')",
            (i+1, 2000+i, f"今天天气{'很好' if i%2==0 else '不好'}", 1700000000+i))
    conn.commit()
    conn.close()
    return cache_dir

def test_build_index(cache_with_messages):
    idx = FtsIndex(cache_with_messages)
    stats = idx.build()
    assert stats["indexed"] == 100
    assert (cache_with_messages / "fts_index.db").exists()

def test_search_fts(cache_with_messages):
    idx = FtsIndex(cache_with_messages)
    idx.build()
    results = idx.search("很好")
    assert len(results) == 50

def test_drop_index(cache_with_messages):
    idx = FtsIndex(cache_with_messages)
    idx.build()
    idx.drop()
    assert not (cache_with_messages / "fts_index.db").exists()

def test_has_index(cache_with_messages):
    idx = FtsIndex(cache_with_messages)
    assert idx.has_index() is False
    idx.build()
    assert idx.has_index() is True
