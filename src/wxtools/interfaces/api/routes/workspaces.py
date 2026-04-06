"""Workspace routes — CRUD for message workspaces."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from wxtools.interfaces.api.dependencies import get_config, verify_token
from wxtools.interfaces.api.models import success_envelope
from wxtools.application import workspace_service
from wxtools.runtime.config import Config

router = APIRouter(tags=["workspaces"], dependencies=[Depends(verify_token)])


class CreateWorkspaceBody(BaseModel):
    name: str
    description: Optional[str] = None


class AddItemsBody(BaseModel):
    items: list[dict[str, Any]]


class UpdateItemBody(BaseModel):
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    title: Optional[str] = None


@router.get("/workspaces")
def list_workspaces(cfg: Config = Depends(get_config)) -> dict:
    """List all workspaces."""
    return success_envelope(workspace_service.list_workspaces(cfg))


@router.post("/workspaces")
def create_workspace(
    body: CreateWorkspaceBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Create a new workspace."""
    return success_envelope(workspace_service.create_workspace(cfg, body.name, body.description))


@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: str, cfg: Config = Depends(get_config)) -> dict:
    """Get a workspace by ID."""
    return success_envelope(workspace_service.get_workspace(cfg, workspace_id))


@router.post("/workspaces/{workspace_id}/items")
def add_items(
    workspace_id: str,
    body: AddItemsBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Add items to a workspace."""
    return success_envelope(workspace_service.add_items(cfg, workspace_id, body.items))


@router.patch("/workspaces/{workspace_id}/items/{item_id}")
def update_item(
    workspace_id: str,
    item_id: str,
    body: UpdateItemBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Update an item's tags, notes, or title."""
    updates = body.model_dump(exclude_none=True)
    return success_envelope(workspace_service.update_item(cfg, workspace_id, item_id, updates))


@router.delete("/workspaces/{workspace_id}/items/{item_id}")
def remove_item(
    workspace_id: str,
    item_id: str,
    cfg: Config = Depends(get_config),
) -> dict:
    """Remove an item from a workspace."""
    return success_envelope(workspace_service.remove_item(cfg, workspace_id, item_id))


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str, cfg: Config = Depends(get_config)) -> dict:
    """Delete a workspace."""
    return success_envelope(workspace_service.delete_workspace(cfg, workspace_id))
