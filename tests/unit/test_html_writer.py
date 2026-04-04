"""Tests for HTML chat bubble export writer."""

from datetime import datetime, timezone


from wxtools.core.schema import Message


def _make_msg(i, is_self=False, conversation_id="conv1", conversation_title="好友A"):
    return Message(
        id=f"db:msg_{i}",
        server_id=1000 + i,
        conversation_id=conversation_id,
        conversation_title=conversation_title,
        sender_id="me" if is_self else "f1",
        sender_name="我" if is_self else "Alice",
        is_self=is_self,
        timestamp=datetime(2026, 1, 1, 12, i, tzinfo=timezone.utc),
        type="text",
        content=f"消息{i}",
        raw_type=1,
        raw_sub_type=0,
        attachment_path=None,
        source_db="message_0.db",
    )


def test_html_writer_produces_valid_html(tmp_path):
    from wxtools.cli.exporters.html_writer import HtmlWriter

    writer = HtmlWriter(tmp_path / "export")
    writer.write_message(_make_msg(0, is_self=False))
    writer.write_message(_make_msg(1, is_self=True))
    manifest = writer.finalize()
    assert manifest["total_messages"] == 2
    html_files = list((tmp_path / "export").rglob("*.html"))
    assert len(html_files) >= 1
    content = html_files[0].read_text("utf-8")
    assert "<html" in content
    assert "消息0" in content
    assert "消息1" in content
    assert "<style>" in content


def test_html_writer_index_page(tmp_path):
    from wxtools.cli.exporters.html_writer import HtmlWriter

    writer = HtmlWriter(tmp_path / "export")
    writer.write_message(_make_msg(0, conversation_id="c1", conversation_title="好友A"))
    writer.write_message(_make_msg(1, conversation_id="c2", conversation_title="好友B"))
    writer.finalize()
    index = tmp_path / "export" / "index.html"
    assert index.exists()
    index_content = index.read_text("utf-8")
    assert "好友A" in index_content
    assert "好友B" in index_content
