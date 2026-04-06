"""Attachment path resolution, existence check, and safe copy."""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger("wxtools.attachment")

_ATTACHMENT_TYPES = {"image", "video", "file", "voice"}
_TYPE_DIRS = {"image": "Image", "video": "Video", "file": "File", "voice": "Voice"}


class AttachmentResolver:
    """Resolve, verify, and copy WeChat attachment files."""

    def __init__(self, data_root: Path) -> None:
        self._root = data_root.resolve()

    def resolve_path(self, msg_type: str, content: str) -> Optional[str]:
        """Resolve attachment path from message type and XML content."""
        if msg_type not in _ATTACHMENT_TYPES:
            return None
        subdir = _TYPE_DIRS.get(msg_type)
        if not subdir:
            return None
        fs_base = self._root / "FileStorage" / subdir
        if not fs_base.is_dir():
            return None
        hint = self._extract_filename_hint(msg_type, content)
        if not hint:
            return None
        for candidate in fs_base.rglob("*"):
            if candidate.is_file() and hint in candidate.name:
                resolved = candidate.resolve()
                if self._is_safe(resolved):
                    return str(resolved)
        return None

    def check_exists(self, path: str) -> bool:
        """Check if attachment file exists, with path traversal protection."""
        try:
            resolved = Path(path).resolve()
        except (ValueError, OSError):
            return False
        if not self._is_safe(resolved):
            logger.warning("Skipping unsafe attachment path: %s", path)
            return False
        return resolved.is_file()

    def copy_to_export(
        self, path: str, export_dir: Path
    ) -> Optional[str]:
        """Copy attachment to export dir, return relative filename or None."""
        try:
            resolved = Path(path).resolve()
        except (ValueError, OSError):
            return None
        if not self._is_safe(resolved):
            logger.warning("Skipping unsafe attachment path: %s", path)
            return None
        if not resolved.is_file():
            return None
        attachments_dir = export_dir / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)
        dest = attachments_dir / resolved.name
        if dest.exists():
            stem, suffix = resolved.stem, resolved.suffix
            counter = 1
            while dest.exists():
                dest = attachments_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        shutil.copy2(resolved, dest)
        return dest.name

    def _is_safe(self, resolved: Path) -> bool:
        """Verify path is within data_root (no traversal)."""
        try:
            resolved.relative_to(self._root)
            return True
        except ValueError:
            return False

    def _extract_filename_hint(
        self, msg_type: str, content: str
    ) -> Optional[str]:
        """Extract filename hint from message XML content."""
        if not content:
            return None
        aeskey = re.search(r'aeskey="([^"]+)"', content)
        if aeskey:
            return aeskey.group(1)
        md5 = re.search(r'md5="([^"]+)"', content)
        if md5:
            return md5.group(1)
        title = re.search(r'title="([^"]+)"', content)
        if title:
            return title.group(1)
        return None
