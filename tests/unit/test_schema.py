from datetime import datetime, timezone
from wxtools.domain.schema import Message, Contact, MessageFilter, QueryResult, VALID_SURFACES


def test_message_creation():
    msg = Message(
        id="MSG0:123",
        server_id=88345678901,
        conversation_id="wxid_abc",
        conversation_title="张三",
        sender_id="wxid_abc",
        sender_name="张三",
        is_self=False,
        timestamp=datetime(2026, 4, 1, 14, 30, tzinfo=timezone.utc),
        type="text",
        content="hello",
        raw_type=1,
        raw_sub_type=0,
        attachment_path=None,
        source_db="MSG0.db",
    )
    assert msg.id == "MSG0:123"
    assert msg.type == "text"


def test_message_to_dict():
    msg = Message(
        id="MSG0:1", server_id=1, conversation_id="wxid_a",
        conversation_title="A", sender_id="wxid_a", sender_name="A",
        is_self=False, timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        type="text", content="hi", raw_type=1, raw_sub_type=0,
        attachment_path=None, source_db="MSG0.db",
    )
    d = msg.to_dict()
    assert d["id"] == "MSG0:1"
    assert d["type"] == "text"
    assert isinstance(d["timestamp"], str)


def test_contact_display_name_priority():
    c1 = Contact(id="wxid_a", nickname="Nick", alias="ali", remark="Rem")
    assert c1.display_name == "Rem"
    c2 = Contact(id="wxid_b", nickname="Nick", alias="ali", remark=None)
    assert c2.display_name == "Nick"
    c3 = Contact(id="wxid_c", nickname=None, alias=None, remark=None)
    assert c3.display_name == "wxid_c"


def test_message_filter_defaults():
    f = MessageFilter()
    assert f.limit == 100
    assert f.offset == 0
    assert f.keyword is None


def test_message_surface_default():
    msg = Message(
        id="MSG0:1", server_id=1, conversation_id="c1",
        conversation_title="A", sender_id="s1", sender_name="A",
        is_self=False, timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        type="text", content="hi", raw_type=1, raw_sub_type=0,
        attachment_path=None, source_db="MSG0.db",
    )
    assert msg.surface == "chat"
    d = msg.to_dict()
    assert d["surface"] == "chat"


def test_message_surface_explicit():
    msg = Message(
        id="PUB:1", server_id=1, conversation_id="gh_abc",
        conversation_title="公众号A", sender_id="gh_abc", sender_name="公众号A",
        is_self=False, timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        type="public_article", content="article", raw_type=49, raw_sub_type=0,
        attachment_path=None, source_db="PublicMsg.db", surface="public",
    )
    assert msg.surface == "public"


def test_valid_surfaces():
    assert "chat" in VALID_SURFACES
    assert "public" in VALID_SURFACES
    assert "moments" in VALID_SURFACES


def test_filter_surface_default():
    f = MessageFilter()
    assert f.surface == "chat"


def test_filter_surface_explicit():
    f = MessageFilter(surface="public")
    assert f.surface == "public"


def test_query_result():
    qr = QueryResult(messages=[], total_estimate=0, has_more=False)
    assert qr.total_estimate == 0
