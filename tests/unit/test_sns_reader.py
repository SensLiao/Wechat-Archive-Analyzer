"""Tests for Moments (SnsReader)."""

import sqlite3
from datetime import datetime, timezone

from wxtools.core.schema import MessageFilter
from wxtools.plugins.wechat.sns_reader import SnsReader, _parse_timeline_xml


def _make_sns_xml(post_id, username, create_time, content_desc):
    return (
        f'<SnsDataItem><TimelineObject>'
        f'<id>{post_id}</id>'
        f'<username>{username}</username>'
        f'<createTime>{create_time}</createTime>'
        f'<contentDesc>{content_desc}</contentDesc>'
        f'<contentDescShowType>0</contentDescShowType>'
        f'</TimelineObject></SnsDataItem>'
    )


def _populate_sns_db(db_path, posts, comments=None):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS SnsTimeLine ("
        "tid INTEGER, user_name TEXT, content TEXT, pack_info_buf TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS SnsMessage_tmp3 ("
        "local_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "create_time INTEGER, type INTEGER, feed_id INTEGER, "
        "is_unread INTEGER, from_username TEXT, from_nickname TEXT, "
        "to_username TEXT, to_nickname TEXT, content TEXT, "
        "serialized_comment_buf BLOB, serialized_ref_buf BLOB, "
        "comment_id INTEGER, client_id TEXT, comment64_id INTEGER, "
        "comment_flag INTEGER, del_status INTEGER, is_relative_me INTEGER)"
    )
    for p in posts:
        xml = _make_sns_xml(p["post_id"], p["username"], p["time"], p["content"])
        conn.execute(
            "INSERT INTO SnsTimeLine (tid, user_name, content) VALUES (?, ?, ?)",
            (p.get("tid", p["post_id"]), p["username"], xml),
        )
    for c in (comments or []):
        conn.execute(
            "INSERT INTO SnsMessage_tmp3 "
            "(create_time, type, feed_id, from_username, from_nickname, content) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (c["time"], c["type"], c["feed_id"], c["from_user"], c.get("from_nick", ""), c.get("content", "")),
        )
    conn.commit()
    conn.close()


def _populate_4x_contact(db_path, contacts):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS contact ("
        "username TEXT PRIMARY KEY, nick_name TEXT, alias TEXT, remark TEXT)"
    )
    for c in contacts:
        conn.execute(
            "INSERT INTO contact (username, nick_name, remark) VALUES (?, ?, ?)",
            (c["id"], c["nick"], c.get("remark")),
        )
    conn.commit()
    conn.close()


def test_parse_timeline_xml():
    xml = _make_sns_xml("12345", "wxid_abc", "1711936200", "今天天气不错")
    result = _parse_timeline_xml(xml)
    assert result is not None
    assert result["post_id"] == "12345"
    assert result["username"] == "wxid_abc"
    assert result["create_time"] == "1711936200"
    assert result["content_desc"] == "今天天气不错"


def test_parse_timeline_xml_invalid():
    assert _parse_timeline_xml("not xml") is None
    assert _parse_timeline_xml("<root>no TimelineObject</root>") is None


def test_sns_reader_search_posts(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    sns_dir = cache_dir / "sns"
    contact_dir = cache_dir / "contact"
    sns_dir.mkdir(parents=True)
    contact_dir.mkdir(parents=True)

    _populate_4x_contact(contact_dir / "contact.db", [
        {"id": "wxid_friend", "nick": "小明"},
    ])
    _populate_sns_db(sns_dir / "sns.db", [
        {"post_id": 1001, "username": "wxid_friend", "time": 1711936200, "content": "今天天气不错"},
        {"post_id": 1002, "username": "wxid_friend", "time": 1711936300, "content": "吃饭了"},
    ])

    reader = SnsReader("wxid_test", str(tmp_path / "cache"))
    result = reader.search()
    assert len(result.messages) == 2
    assert all(m.surface == "moments" for m in result.messages)
    assert all(m.type == "sns_post" for m in result.messages)
    assert result.messages[0].content == "今天天气不错"
    assert result.messages[0].sender_name == "小明"


def test_sns_reader_search_keyword(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    sns_dir = cache_dir / "sns"
    contact_dir = cache_dir / "contact"
    sns_dir.mkdir(parents=True)
    contact_dir.mkdir(parents=True)

    _populate_4x_contact(contact_dir / "contact.db", [])
    _populate_sns_db(sns_dir / "sns.db", [
        {"post_id": 2001, "username": "wxid_a", "time": 1711936200, "content": "周末去爬山"},
        {"post_id": 2002, "username": "wxid_b", "time": 1711936300, "content": "下雨了"},
    ])

    reader = SnsReader("wxid_test", str(tmp_path / "cache"))
    result = reader.search(keyword="爬山")
    assert len(result.messages) == 1
    assert "爬山" in result.messages[0].content


def test_sns_reader_comments(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    sns_dir = cache_dir / "sns"
    contact_dir = cache_dir / "contact"
    sns_dir.mkdir(parents=True)
    contact_dir.mkdir(parents=True)

    _populate_4x_contact(contact_dir / "contact.db", [])
    _populate_sns_db(
        sns_dir / "sns.db",
        posts=[{"post_id": 3001, "username": "wxid_a", "time": 1711936200, "content": "帖子"}],
        comments=[
            {"time": 1711936300, "type": 2, "feed_id": 3001, "from_user": "wxid_b", "from_nick": "小红", "content": "好棒"},
            {"time": 1711936400, "type": 1, "feed_id": 3001, "from_user": "wxid_c", "from_nick": "小刚", "content": ""},
        ],
    )

    reader = SnsReader("wxid_test", str(tmp_path / "cache"))
    result = reader.search()
    assert len(result.messages) == 3  # 1 post + 1 comment + 1 like
    types = {m.type for m in result.messages}
    assert "sns_post" in types
    assert "sns_comment" in types
    assert "sns_like" in types


def test_sns_reader_date_filter(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    sns_dir = cache_dir / "sns"
    contact_dir = cache_dir / "contact"
    sns_dir.mkdir(parents=True)
    contact_dir.mkdir(parents=True)

    _populate_4x_contact(contact_dir / "contact.db", [])
    _populate_sns_db(sns_dir / "sns.db", [
        {"post_id": 4001, "username": "wxid_a", "time": 1704067200, "content": "新年快乐"},  # 2024-01-01
        {"post_id": 4002, "username": "wxid_a", "time": 1711936200, "content": "春天来了"},  # 2024-04-01
    ])

    reader = SnsReader("wxid_test", str(tmp_path / "cache"))
    result = reader.search(filters=MessageFilter(
        since=datetime(2024, 3, 1, tzinfo=timezone.utc),
        surface="moments",
    ))
    assert len(result.messages) == 1
    assert result.messages[0].content == "春天来了"


def test_sns_reader_iter_messages(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    sns_dir = cache_dir / "sns"
    contact_dir = cache_dir / "contact"
    sns_dir.mkdir(parents=True)
    contact_dir.mkdir(parents=True)

    _populate_4x_contact(contact_dir / "contact.db", [])
    _populate_sns_db(sns_dir / "sns.db", [
        {"post_id": 5001, "username": "wxid_a", "time": 1711936200, "content": "msg1"},
        {"post_id": 5002, "username": "wxid_a", "time": 1711936300, "content": "msg2"},
    ])

    reader = SnsReader("wxid_test", str(tmp_path / "cache"))
    msgs = list(reader.iter_messages(MessageFilter(surface="moments", limit=1)))
    assert len(msgs) == 1
