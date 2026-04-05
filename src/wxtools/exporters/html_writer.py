"""Streaming HTML chat bubble export writer."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Dict, List, Optional

from wxtools.core.schema import Message

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

_CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #ebebeb; padding: 20px; max-width: 800px; margin: 0 auto; }
h1 { text-align: center; margin-bottom: 20px; font-size: 1.2em; color: #333; }
.date-sep { text-align: center; margin: 16px 0 8px; font-size: 0.85em; color: #999; }
.msg { display: flex; margin: 8px 0; align-items: flex-start; }
.msg.self { flex-direction: row-reverse; }
.avatar { width: 40px; height: 40px; border-radius: 4px; background: #ccc; display: flex; align-items: center; justify-content: center; font-size: 14px; color: #fff; flex-shrink: 0; }
.msg.self .avatar { background: #7bb342; }
.bubble-wrap { max-width: 70%; margin: 0 10px; }
.sender { font-size: 0.75em; color: #888; margin-bottom: 2px; }
.msg.self .sender { text-align: right; }
.bubble { padding: 10px 14px; border-radius: 8px; background: #fff; word-wrap: break-word; line-height: 1.5; position: relative; }
.msg.self .bubble { background: #95ec69; }
.time { font-size: 0.7em; color: #aaa; margin-top: 2px; }
.msg.self .time { text-align: right; }
.bubble img { max-width: 100%; border-radius: 4px; }
.index-list { list-style: none; padding: 0; }
.index-list li { padding: 12px 16px; background: #fff; margin: 4px 0; border-radius: 8px; }
.index-list li a { text-decoration: none; color: #333; font-size: 1em; }
.index-list li a:hover { color: #07c160; }
"""


def _sanitize_filename(name: str, max_len: int = 200) -> str:
    safe = _ILLEGAL_CHARS.sub("_", name)
    if len(safe) > max_len:
        h = hashlib.md5(name.encode()).hexdigest()[:8]
        safe = safe[:max_len] + "_" + h
    return safe or "unnamed"


class HtmlWriter:
    """Streaming writer that produces chat-bubble HTML files."""

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
        self._output_dir.mkdir(parents=True, exist_ok=True)
        total = sum(len(msgs) for msgs in self._conversations.values())
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()

        files_info: List[dict] = []

        if len(self._conversations) <= 1:
            for cid, msgs in self._conversations.items():
                title = self._conversation_titles.get(cid, cid)
                filename = _sanitize_filename(title) + ".html"
                filepath = self._output_dir / filename
                self._write_html_file(filepath, title, msgs)
                files_info.append({
                    "path": str(filepath.relative_to(self._output_dir)),
                    "conversation_id": cid,
                    "message_count": len(msgs),
                })
        else:
            convos_dir = self._output_dir / "conversations"
            convos_dir.mkdir(parents=True, exist_ok=True)

            index_entries: List[dict] = []

            for cid in sorted(self._conversations):
                msgs = self._conversations[cid]
                title = self._conversation_titles.get(cid, cid)
                filename = _sanitize_filename(title) + ".html"
                filepath = convos_dir / filename

                counter = 1
                while filepath.exists():
                    filepath = convos_dir / f"{_sanitize_filename(title)}_{counter}.html"
                    counter += 1

                self._write_html_file(filepath, title, msgs)

                rel = str(filepath.relative_to(self._output_dir))
                time_range = []
                if msgs:
                    time_range = [
                        msgs[0].timestamp.isoformat(),
                        msgs[-1].timestamp.isoformat(),
                    ]
                files_info.append({
                    "path": rel,
                    "conversation_id": cid,
                    "message_count": len(msgs),
                    "time_range": time_range,
                })
                index_entries.append({"title": title, "href": rel, "count": len(msgs)})

            # Write index.html
            self._write_index(self._output_dir / "index.html", index_entries)

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
    def _write_html_file(filepath: Path, title: str, messages: List[Message]) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        parts: List[str] = []
        parts.append(f"""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>{escape(title)}</h1>
""")

        last_date: Optional[str] = None
        for msg in messages:
            msg_date = msg.timestamp.strftime("%Y-%m-%d")
            if msg_date != last_date:
                parts.append(f'<div class="date-sep">{escape(msg_date)}</div>\n')
                last_date = msg_date

            cls = "msg self" if msg.is_self else "msg"
            initial = escape(msg.sender_name[:1]) if msg.sender_name else "?"
            time_str = msg.timestamp.strftime("%H:%M")

            # Content rendering
            if msg.type == "image" and msg.attachment_path:
                content_html = f'<img src="{escape(msg.attachment_path)}" alt="image">'
            else:
                content_html = escape(msg.content).replace("\n", "<br>")

            parts.append(f"""\
<div class="{cls}">
  <div class="avatar">{initial}</div>
  <div class="bubble-wrap">
    <div class="sender">{escape(msg.sender_name)}</div>
    <div class="bubble">{content_html}</div>
    <div class="time">{time_str}</div>
  </div>
</div>
""")

        parts.append("</body>\n</html>\n")
        filepath.write_text("".join(parts), encoding="utf-8")

    @staticmethod
    def _write_index(filepath: Path, entries: List[dict]) -> None:
        parts: List[str] = []
        parts.append(f"""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chat Export Index</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Chat Export Index</h1>
<ul class="index-list">
""")
        for entry in entries:
            parts.append(
                f'<li><a href="{escape(entry["href"])}">'
                f'{escape(entry["title"])} ({entry["count"]} messages)</a></li>\n'
            )
        parts.append("</ul>\n</body>\n</html>\n")
        filepath.write_text("".join(parts), encoding="utf-8")
