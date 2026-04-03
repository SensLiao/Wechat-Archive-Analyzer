import sqlite3
from pathlib import Path
from wxtools.plugins.wechat.db_reader import DbReader


def _populate_msg_db(db_path, messages):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS MSG ("
        "localId INTEGER PRIMARY KEY, TalkerId INTEGER, MsgSvrID INTEGER, "
        "Type INTEGER, SubType INTEGER, CreateTime INTEGER, IsSender INTEGER, "
        "Sequence INTEGER, StrTalker TEXT, StrContent TEXT, "
        "DisplayContent TEXT, BytesExtra BLOB, CompressContent BLOB)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS Name2ID (rowId INTEGER PRIMARY KEY, UsrName TEXT)")
    for msg in messages:
        conn.execute(
            "INSERT INTO MSG (localId, MsgSvrID, Type, SubType, CreateTime, IsSender, StrTalker, StrContent) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (msg["id"], msg["srv_id"], 1, 0, msg["time"], 0, msg["talker"], msg["content"]),
        )
    conn.commit()
    conn.close()


def _populate_micromsg(db_path, contacts):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS Contact ("
        "UserName TEXT PRIMARY KEY, Alias TEXT, Remark TEXT, NickName TEXT, "
        "Type INTEGER, smallHeadImgUrl TEXT, bigHeadImgUrl TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ChatRoom ("
        "ChatRoomName TEXT PRIMARY KEY, UserNameList TEXT, DisplayNameList TEXT, RoomData BLOB)"
    )
    for c in contacts:
        conn.execute(
            "INSERT INTO Contact (UserName, NickName, Remark) VALUES (?, ?, ?)",
            (c["id"], c["nick"], c.get("remark")),
        )
    conn.commit()
    conn.close()


def test_search_keyword(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    cache_dir.mkdir(parents=True)
    _populate_msg_db(cache_dir / "MSG0.db", [
        {"id": 1, "srv_id": 1001, "time": 1711936200, "talker": "wxid_a", "content": "hello 开会"},
        {"id": 2, "srv_id": 1002, "time": 1711936300, "talker": "wxid_a", "content": "bye"},
    ])
    _populate_micromsg(cache_dir / "MicroMsg.db", [
        {"id": "wxid_a", "nick": "张三", "remark": None},
    ])
    reader = DbReader("wxid_test", str(tmp_path / "cache"))
    result = reader.search(keyword="开会")
    assert len(result.messages) == 1
    assert "开会" in result.messages[0].content


def test_search_cross_shard(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    cache_dir.mkdir(parents=True)
    _populate_msg_db(cache_dir / "MSG0.db", [
        {"id": 1, "srv_id": 2001, "time": 1711936200, "talker": "wxid_a", "content": "shard0 msg"},
    ])
    _populate_msg_db(cache_dir / "MSG1.db", [
        {"id": 1, "srv_id": 2002, "time": 1711936300, "talker": "wxid_a", "content": "shard1 msg"},
    ])
    _populate_micromsg(cache_dir / "MicroMsg.db", [
        {"id": "wxid_a", "nick": "张三"},
    ])
    reader = DbReader("wxid_test", str(tmp_path / "cache"))
    result = reader.search()
    assert len(result.messages) == 2


def test_search_with_limit(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    cache_dir.mkdir(parents=True)
    msgs = [{"id": i, "srv_id": 3000 + i, "time": 1711936200 + i, "talker": "wxid_a", "content": f"msg {i}"} for i in range(20)]
    _populate_msg_db(cache_dir / "MSG0.db", msgs)
    _populate_micromsg(cache_dir / "MicroMsg.db", [{"id": "wxid_a", "nick": "A"}])
    reader = DbReader("wxid_test", str(tmp_path / "cache"))
    from wxtools.core.schema import MessageFilter
    result = reader.search(filters=MessageFilter(limit=5))
    assert len(result.messages) == 5
    assert result.has_more is True


def test_query_sql(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    cache_dir.mkdir(parents=True)
    _populate_msg_db(cache_dir / "MSG0.db", [
        {"id": 1, "srv_id": 4001, "time": 1711936200, "talker": "wxid_a", "content": "test"},
    ])
    _populate_micromsg(cache_dir / "MicroMsg.db", [])
    reader = DbReader("wxid_test", str(tmp_path / "cache"))
    rows = reader.query_sql("SELECT count(*) as cnt FROM MSG", db_name="MSG0.db")
    assert rows[0]["cnt"] == 1


def test_resolve_contact(tmp_path):
    cache_dir = tmp_path / "cache" / "wxid_test"
    cache_dir.mkdir(parents=True)
    _populate_micromsg(cache_dir / "MicroMsg.db", [
        {"id": "wxid_a", "nick": "Alice", "remark": "A同学"},
    ])
    reader = DbReader("wxid_test", str(tmp_path / "cache"))
    contact = reader.resolve_contact("wxid_a")
    assert contact is not None
    assert contact.display_name == "A同学"
