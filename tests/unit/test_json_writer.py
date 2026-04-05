"""Tests for streaming JSON export writer."""

from datetime import datetime, timezone


from wxtools.core.schema import Message


def _make_msg(i, conversation_id="conv1", conversation_title="好友A"):
    return Message(
        id=f"db:msg_{i}",
        server_id=1000 + i,
        conversation_id=conversation_id,
        conversation_title=conversation_title,
        sender_id="friend1",
        sender_name="Alice",
        is_self=False,
        timestamp=datetime(2026, 1, 1, 12, i, tzinfo=timezone.utc),
        type="text",
        content=f"消息{i}",
        raw_type=1,
        raw_sub_type=0,
        attachment_path=None,
        source_db="message_0.db",
    )


def test_json_writer_single_conversation(tmp_path):
    from wxtools.exporters.json_writer import JsonWriter

    writer = JsonWriter(tmp_path / "export")
    for i in range(5):
        writer.write_message(_make_msg(i))
    manifest = writer.finalize()
    assert manifest["total_messages"] == 5
    assert manifest["total_conversations"] == 1
    conv_files = list((tmp_path / "export").rglob("*.json"))
    assert len(conv_files) >= 1


def test_json_writer_multiple_conversations(tmp_path):
    from wxtools.exporters.json_writer import JsonWriter

    writer = JsonWriter(tmp_path / "export")
    for i in range(3):
        writer.write_message(_make_msg(i, "conv1", "好友A"))
    for i in range(2):
        writer.write_message(_make_msg(10 + i, "conv2", "好友B"))
    manifest = writer.finalize()
    assert manifest["total_messages"] == 5
    assert manifest["total_conversations"] == 2
