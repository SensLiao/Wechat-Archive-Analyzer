"""Tests for CSV export writer."""

import csv
from datetime import datetime, timezone


from wxtools.domain.schema import Message


def _make_msg(i, conversation_title="好友A"):
    return Message(
        id=f"db:msg_{i}",
        server_id=1000 + i,
        conversation_id="conv1",
        conversation_title=conversation_title,
        sender_id="f1",
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


def test_csv_writer_produces_valid_csv(tmp_path):
    from wxtools.infrastructure.exporters.csv_writer import CsvWriter

    writer = CsvWriter(tmp_path / "export")
    for i in range(5):
        writer.write_message(_make_msg(i))
    manifest = writer.finalize()
    assert manifest["total_messages"] == 5
    csv_files = list((tmp_path / "export").rglob("*.csv"))
    assert len(csv_files) >= 1
    raw = csv_files[0].read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf"  # UTF-8 BOM
    rows = list(csv.reader(raw.decode("utf-8-sig").splitlines()))
    header = rows[0]
    assert "timestamp" in header
    assert "sender" in header
    assert "content" in header
    assert len(rows) == 6  # header + 5 data
