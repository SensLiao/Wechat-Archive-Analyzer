from wxtools.infrastructure.wechat.schema_mapper import row_to_message, row_to_contact, map_message_type

def test_row_to_message_text():
    row = {
        "localId": 1, "MsgSvrID": 99999, "Type": 1, "SubType": 0,
        "CreateTime": 1711936200, "IsSender": 0, "StrTalker": "wxid_abc",
        "StrContent": "hello world", "DisplayContent": "",
        "BytesExtra": None, "CompressContent": None,
    }
    msg = row_to_message(row, "MSG0.db", sender_name="张三", conversation_title="张三")
    assert msg.type == "text"
    assert msg.content == "hello world"
    assert msg.id == "MSG0:1"
    assert msg.server_id == 99999
    assert msg.source_db == "MSG0.db"
    assert msg.is_self is False


def test_row_to_message_image():
    row = {
        "localId": 2, "MsgSvrID": 100000, "Type": 3, "SubType": 0,
        "CreateTime": 1711936200, "IsSender": 1, "StrTalker": "wxid_abc",
        "StrContent": "<msg><img /></msg>", "DisplayContent": "",
        "BytesExtra": None, "CompressContent": None,
    }
    msg = row_to_message(row, "MSG0.db", sender_name="我", conversation_title="张三")
    assert msg.type == "image"
    assert msg.is_self is True


def test_row_to_message_system():
    row = {
        "localId": 3, "MsgSvrID": 100001, "Type": 10000, "SubType": 0,
        "CreateTime": 1711936200, "IsSender": 0, "StrTalker": "wxid_abc",
        "StrContent": "你撤回了一条消息", "DisplayContent": "你撤回了一条消息",
        "BytesExtra": None, "CompressContent": None,
    }
    msg = row_to_message(row, "MSG0.db", sender_name="系统", conversation_title="张三")
    assert msg.type == "system"


def test_row_to_contact():
    row = {"UserName": "wxid_abc", "NickName": "张三", "Alias": "zs", "Remark": "三哥"}
    contact = row_to_contact(row)
    assert contact.id == "wxid_abc"
    assert contact.display_name == "三哥"


def test_map_message_type():
    assert map_message_type(1, 0) == "text"
    assert map_message_type(3, 0) == "image"
    assert map_message_type(34, 0) == "voice"
    assert map_message_type(43, 0) == "video"
    assert map_message_type(49, 6) == "file"
    assert map_message_type(10000, 0) == "system"
    assert map_message_type(99999, 0) == "unknown"
