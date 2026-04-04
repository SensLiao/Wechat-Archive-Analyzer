"""Tests for DbReader count_messages, search_page, iter_messages."""
import sqlite3
import hashlib
from pathlib import Path
import pytest
from wxtools.core.schema import MessageFilter
from wxtools.plugins.wechat.db_reader import DbReader


@pytest.fixture
def reader_4x(tmp_path):
    account = "wxid_pager"
    cache_dir = tmp_path / account
    contact_dir = cache_dir / "contact"
    contact_dir.mkdir(parents=True)
    conn = sqlite3.connect(contact_dir / "contact.db")
    conn.execute("CREATE TABLE contact (username TEXT, nick_name TEXT, alias TEXT, remark TEXT)")
    conn.execute("INSERT INTO contact VALUES ('friend1', 'Alice', '', '')")
    conn.commit()
    conn.close()
    msg_dir = cache_dir / "message"
    msg_dir.mkdir(parents=True)
    conn = sqlite3.connect(msg_dir / "message_0.db")
    conn.execute("CREATE TABLE Name2Id (user_name TEXT)")
    conn.execute("INSERT INTO Name2Id VALUES ('friend1')")
    table_hash = hashlib.md5(b"friend1").hexdigest()
    table_name = f"Msg_{table_hash}"
    conn.execute(f"""CREATE TABLE {table_name} (
        local_id INTEGER PRIMARY KEY, server_id INTEGER, local_type INTEGER,
        sender_wxid TEXT, message_content TEXT, create_time INTEGER, display_content TEXT
    )""")
    for i in range(25):
        conn.execute(f"INSERT INTO {table_name} VALUES (?, ?, 1, 'friend1', ?, ?, '')",
            (i + 1, 1000 + i, f"msg{i}", 1700000000 + i * 60))
    conn.commit()
    conn.close()
    return DbReader(account, tmp_path)


def test_count_messages(reader_4x):
    f = MessageFilter(keyword="msg")
    count = reader_4x.count_messages(f)
    assert count == 25


def test_count_with_keyword_filter(reader_4x):
    f = MessageFilter(keyword="msg1")
    count = reader_4x.count_messages(f)
    assert count == 11  # msg1, msg10-msg19


def test_search_page(reader_4x):
    f = MessageFilter(keyword="msg", limit=10, offset=0)
    result = reader_4x.search_page(f)
    assert len(result.messages) == 10
    assert result.has_more is True
    assert result.total_estimate == 25


def test_search_page_offset(reader_4x):
    f = MessageFilter(keyword="msg", limit=10, offset=20)
    result = reader_4x.search_page(f)
    assert len(result.messages) == 5
    assert result.has_more is False


def test_iter_messages(reader_4x):
    f = MessageFilter(keyword="msg")
    messages = list(reader_4x.iter_messages(f))
    assert len(messages) == 25


def test_iter_messages_with_limit(reader_4x):
    f = MessageFilter(keyword="msg", limit=5)
    messages = list(reader_4x.iter_messages(f))
    assert len(messages) == 5
