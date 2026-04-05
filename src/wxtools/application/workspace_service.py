"""Workspace management service.

Workspaces are user-defined collections of search results, messages, and notes.
Each workspace is stored as a single JSON file under ``cfg.home_dir / "workspaces"``.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wxtools.core.errors import WxToolsError

if TYPE_CHECKING:
    from wxtools.core.config import Config

logger = logging.getLogger("wxtools.application.workspace")


# ---------------------------------------------------------------------------
# Error subclasses
# ---------------------------------------------------------------------------

class WorkspaceNotFoundError(WxToolsError):
    def __init__(self, workspace_id: str):
        super().__init__(
            "WORKSPACE_NOT_FOUND",
            f"Workspace not found: {workspace_id}",
            "Check workspace ID with 'list_workspaces'.",
        )


class WorkspaceItemNotFoundError(WxToolsError):
    def __init__(self, item_id: str):
        super().__init__(
            "WORKSPACE_ITEM_NOT_FOUND",
            f"Workspace item not found: {item_id}",
            "Check item ID with 'get_workspace'.",
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _workspaces_dir(cfg: Config) -> Path:
    """Return (and ensure) the workspaces storage directory."""
    d = cfg.home_dir / "workspaces"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _workspace_path(cfg: Config, workspace_id: str) -> Path:
    """Return the file path for a workspace JSON file."""
    return _workspaces_dir(cfg) / f"{workspace_id}.json"


def _read_workspace(cfg: Config, workspace_id: str) -> dict[str, Any]:
    """Read and parse a workspace file.

    Raises:
        WorkspaceNotFoundError: When the file does not exist.
    """
    path = _workspace_path(cfg, workspace_id)
    if not path.is_file():
        raise WorkspaceNotFoundError(workspace_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise WxToolsError(
            "WORKSPACE_CORRUPT",
            f"Failed to read workspace {workspace_id}: {exc}",
            "Delete and recreate the workspace.",
        ) from exc


def _write_workspace(cfg: Config, data: dict[str, Any]) -> None:
    """Write a workspace dict to its JSON file."""
    path = _workspace_path(cfg, data["id"])
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_workspaces(cfg: Config) -> list[dict[str, Any]]:
    """List all workspaces (summary only, without full item lists).

    Returns:
        A list of workspace summary dicts (id, name, description,
        created_at, updated_at, item_count).
    """
    ws_dir = _workspaces_dir(cfg)
    results: list[dict[str, Any]] = []

    for f in sorted(ws_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(
                {
                    "id": data["id"],
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "item_count": len(data.get("items", [])),
                }
            )
        except (json.JSONDecodeError, KeyError, OSError):
            logger.warning("Skipping corrupt workspace file: %s", f)

    return results


def create_workspace(
    cfg: Config,
    name: str,
    description: str = "",
) -> dict[str, Any]:
    """Create a new workspace.

    Returns:
        The full workspace dict (with empty items list).
    """
    now = _now_iso()
    workspace: dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "name": name,
        "description": description,
        "created_at": now,
        "updated_at": now,
        "items": [],
    }
    _write_workspace(cfg, workspace)
    return workspace


def get_workspace(cfg: Config, workspace_id: str) -> dict[str, Any]:
    """Get the full workspace data including all items.

    Raises:
        WorkspaceNotFoundError: When workspace does not exist.
    """
    return _read_workspace(cfg, workspace_id)


def add_items(
    cfg: Config,
    workspace_id: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Add items to a workspace.

    Each item dict should contain at least ``type`` and ``title``.  Missing
    ``id`` fields are auto-generated.

    Returns:
        The updated workspace dict.

    Raises:
        WorkspaceNotFoundError: When workspace does not exist.
    """
    workspace = _read_workspace(cfg, workspace_id)
    now = _now_iso()

    for item in items:
        if "id" not in item:
            item["id"] = uuid.uuid4().hex
        # Ensure required fields have defaults
        item.setdefault("type", "note")
        item.setdefault("source_id", "")
        item.setdefault("surface", "")
        item.setdefault("title", "")
        item.setdefault("content_preview", "")
        item.setdefault("timestamp", now)
        item.setdefault("tags", [])
        item.setdefault("notes", "")

    workspace["items"].extend(items)
    workspace["updated_at"] = now
    _write_workspace(cfg, workspace)
    return workspace


def remove_item(
    cfg: Config,
    workspace_id: str,
    item_id: str,
) -> dict[str, Any]:
    """Remove an item from a workspace by item ID.

    Returns:
        The updated workspace dict.

    Raises:
        WorkspaceNotFoundError: When workspace does not exist.
        WorkspaceItemNotFoundError: When item is not found.
    """
    workspace = _read_workspace(cfg, workspace_id)
    original_len = len(workspace["items"])
    workspace["items"] = [i for i in workspace["items"] if i.get("id") != item_id]

    if len(workspace["items"]) == original_len:
        raise WorkspaceItemNotFoundError(item_id)

    workspace["updated_at"] = _now_iso()
    _write_workspace(cfg, workspace)
    return workspace


def delete_workspace(cfg: Config, workspace_id: str) -> dict[str, Any]:
    """Delete a workspace entirely.

    Returns:
        Dict with ``id`` and ``deleted`` flag.

    Raises:
        WorkspaceNotFoundError: When workspace does not exist.
    """
    path = _workspace_path(cfg, workspace_id)
    if not path.is_file():
        raise WorkspaceNotFoundError(workspace_id)

    path.unlink()
    return {"id": workspace_id, "deleted": True}
