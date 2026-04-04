"""Streaming CSV export writer."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from wxtools.core.schema import Message

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

_CSV_HEADER = ["timestamp", "sender", "conversation", "type", "content", "attachment_path"]


def _sanitize_filename(name: str, max_len: int = 200) -> str:
    """Sanitize a string for use as a filename on Windows."""
    safe = _ILLEGAL_CHARS.sub("_", name)
    if len(safe) > max_len:
        h = hashlib.md5(name.encode()).hexdigest()[:8]
        safe = safe[:max_len] + "_" + h
    return safe or "unnamed"


class CsvWriter:
    """Streaming writer that groups messages by conversation and writes CSV files."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = Path(output_dir)
        self._conversations: Dict[str, List[Message]] = {}
        self._conversation_titles: Dict[str, str] = {}

    def write_message(self, msg: Message) -> None:
        cid = msg.conversation_id
        self._conversations.setdefault(cid, []).append(msg)
        if cid not in self._conversation_titles:
            self._conversation_titles[cid] = msg.conversation_title

    def finalize(self) -> dict:
        """Write per-conversation CSV files and manifest. Returns manifest dict."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        total = sum(len(msgs) for msgs in self._conversations.values())
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()

        files_info: List[dict] = []

        if len(self._conversations) <= 1:
            for cid, msgs in self._conversations.items():
                title = self._conversation_titles.get(cid, cid)
                filename = _sanitize_filename(title) + ".csv"
                filepath = self._output_dir / filename
                self._write_csv_file(filepath, msgs)
                files_info.append({
                    "path": str(filepath.relative_to(self._output_dir)),
                    "conversation_id": cid,
                    "message_count": len(msgs),
                })
        else:
            convos_dir = self._output_dir / "conversations"
            convos_dir.mkdir(parents=True, exist_ok=True)

            for cid in sorted(self._conversations):
                msgs = self._conversations[cid]
                title = self._conversation_titles.get(cid, cid)
                filename = _sanitize_filename(title) + ".csv"
                filepath = convos_dir / filename

                counter = 1
                while filepath.exists():
                    filepath = convos_dir / f"{_sanitize_filename(title)}_{counter}.csv"
                    counter += 1

                self._write_csv_file(filepath, msgs)

                time_range = []
                if msgs:
                    time_range = [
                        msgs[0].timestamp.isoformat(),
                        msgs[-1].timestamp.isoformat(),
                    ]
                files_info.append({
                    "path": str(filepath.relative_to(self._output_dir)),
                    "conversation_id": cid,
                    "message_count": len(msgs),
                    "time_range": time_range,
                })

        manifest = {
            "exported_at": now_iso,
            "total_messages": total,
            "total_conversations": len(self._conversations),
            "files": files_info,
        }

        if len(self._conversations) > 1:
            manifest_path = self._output_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        return manifest

    @staticmethod
    def _write_csv_file(filepath: Path, messages: List[Message]) -> None:
        """Write messages to a UTF-8 BOM CSV file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(_CSV_HEADER)
            for msg in messages:
                writer.writerow([
                    msg.timestamp.isoformat(),
                    msg.sender_name,
                    msg.conversation_title,
                    msg.type,
                    msg.content,
                    msg.attachment_path or "",
                ])
