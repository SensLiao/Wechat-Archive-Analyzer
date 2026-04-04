"""Shared test fixtures for wxtools."""

import sqlite3

import pytest


@pytest.fixture
def tmp_home(tmp_path):
    """Provide a temporary ~/.wxtools/ directory."""
    home = tmp_path / ".wxtools"
    home.mkdir()
    (home / "keys").mkdir()
    (home / "cache").mkdir()
    (home / "logs").mkdir()
    return home


@pytest.fixture
def plain_sqlite_db(tmp_path):
    """Create a minimal plain SQLite DB for testing reads (not encrypted)."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE MSG ("
        "localId INTEGER PRIMARY KEY, TalkerId INTEGER, MsgSvrID INTEGER, "
        "Type INTEGER, SubType INTEGER, CreateTime INTEGER, IsSender INTEGER, "
        "Sequence INTEGER, StrTalker TEXT, StrContent TEXT, "
        "DisplayContent TEXT, BytesExtra BLOB, CompressContent BLOB)"
    )
    conn.execute(
        "CREATE TABLE Name2ID (rowId INTEGER PRIMARY KEY, UsrName TEXT)"
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def micromsg_db(tmp_path):
    """Create a minimal MicroMsg.db with Contact and ChatRoom tables."""
    db_path = tmp_path / "MicroMsg.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE Contact ("
        "UserName TEXT PRIMARY KEY, Alias TEXT, Remark TEXT, NickName TEXT, "
        "Type INTEGER, smallHeadImgUrl TEXT, bigHeadImgUrl TEXT)"
    )
    conn.execute(
        "CREATE TABLE ChatRoom ("
        "ChatRoomName TEXT PRIMARY KEY, UserNameList TEXT, "
        "DisplayNameList TEXT, RoomData BLOB)"
    )
    conn.commit()
    conn.close()
    return db_path
