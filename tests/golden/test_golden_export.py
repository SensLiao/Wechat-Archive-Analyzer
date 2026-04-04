"""Golden output tests: export synthetic DB and compare with expected."""
import json
import csv
from pathlib import Path
import pytest
from wxtools.cli.exporters.json_writer import JsonWriter
from wxtools.cli.exporters.csv_writer import CsvWriter
from wxtools.cli.exporters.html_writer import HtmlWriter
from wxtools.core.schema import Message
from datetime import datetime, timezone

GOLDEN_MESSAGES = [
    Message(
        id="golden:1", server_id=1001,
        conversation_id="test_conv", conversation_title="测试会话",
        sender_id="friend", sender_name="小明", is_self=False,
        timestamp=datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
        type="text", content="你好，这是一条测试消息",
        raw_type=1, raw_sub_type=0, attachment_path=None, source_db="message_0.db",
    ),
    Message(
        id="golden:2", server_id=1002,
        conversation_id="test_conv", conversation_title="测试会话",
        sender_id="me", sender_name="我", is_self=True,
        timestamp=datetime(2026, 1, 15, 10, 31, tzinfo=timezone.utc),
        type="text", content="收到！",
        raw_type=1, raw_sub_type=0, attachment_path=None, source_db="message_0.db",
    ),
]


def test_golden_json(tmp_path):
    writer = JsonWriter(tmp_path / "json_export")
    for msg in GOLDEN_MESSAGES:
        writer.write_message(msg)
    manifest = writer.finalize()
    assert manifest["total_messages"] == 2
    assert manifest["total_conversations"] == 1
    conv_file = tmp_path / "json_export" / "测试会话.json"
    assert conv_file.exists()
    data = json.loads(conv_file.read_text("utf-8"))
    assert data["messages"][0]["content"] == "你好，这是一条测试消息"
    assert data["messages"][1]["content"] == "收到！"
    assert data["messages"][0]["sender_name"] == "小明"
    assert data["messages"][1]["is_self"] is True


def test_golden_csv(tmp_path):
    writer = CsvWriter(tmp_path / "csv_export")
    for msg in GOLDEN_MESSAGES:
        writer.write_message(msg)
    writer.finalize()
    csv_file = tmp_path / "csv_export" / "测试会话.csv"
    assert csv_file.exists()
    rows = list(csv.reader(csv_file.read_text("utf-8-sig").splitlines()))
    assert rows[0] == ["timestamp", "sender", "conversation", "type", "content", "attachment_path"]
    assert rows[1][1] == "小明"
    assert rows[1][4] == "你好，这是一条测试消息"
    assert rows[2][1] == "我"


def test_golden_html(tmp_path):
    writer = HtmlWriter(tmp_path / "html_export")
    for msg in GOLDEN_MESSAGES:
        writer.write_message(msg)
    writer.finalize()
    html_file = tmp_path / "html_export" / "测试会话.html"
    assert html_file.exists()
    content = html_file.read_text("utf-8")
    assert "你好，这是一条测试消息" in content
    assert "收到！" in content
    assert "<style>" in content
