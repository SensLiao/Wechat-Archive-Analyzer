"""Workspace routes — CRUD for message workspaces."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from wxtools.api.dependencies import get_config, verify_token
from wxtools.services import workspace_service
from wxtools.core.config import Config
from wxtools.core.errors import WxToolsError

router = APIRouter(tags=["workspaces"], dependencies=[Depends(verify_token)])


def _status_for(code: str) -> int:
    mapping = {
        "WORKSPACE_NOT_FOUND": 404,
        "WORKSPACE_ITEM_NOT_FOUND": 404,
        "PLATFORM_NOT_SUPPORTED": 501,
    }
    return mapping.get(code, 500)


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
def list_workspaces(cfg: Config = Depends(get_config)) -> list[dict]:
    """List all workspaces."""
    try:
        return workspace_service.list_workspaces(cfg)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.post("/workspaces")
def create_workspace(
    body: CreateWorkspaceBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Create a new workspace."""
    try:
        return workspace_service.create_workspace(cfg, body.name, body.description)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: str, cfg: Config = Depends(get_config)) -> dict:
    """Get a workspace by ID."""
    try:
        return workspace_service.get_workspace(cfg, workspace_id)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.post("/workspaces/{workspace_id}/items")
def add_items(
    workspace_id: str,
    body: AddItemsBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Add items to a workspace."""
    try:
        return workspace_service.add_items(cfg, workspace_id, body.items)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.patch("/workspaces/{workspace_id}/items/{item_id}")
def update_item(
    workspace_id: str,
    item_id: str,
    body: UpdateItemBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Update an item's tags, notes, or title."""
    try:
        updates = body.model_dump(exclude_none=True)
        return workspace_service.update_item(cfg, workspace_id, item_id, updates)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.delete("/workspaces/{workspace_id}/items/{item_id}")
def remove_item(
    workspace_id: str,
    item_id: str,
    cfg: Config = Depends(get_config),
) -> dict:
    """Remove an item from a workspace."""
    try:
        return workspace_service.remove_item(cfg, workspace_id, item_id)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str, cfg: Config = Depends(get_config)) -> dict:
    """Delete a workspace."""
    try:
        return workspace_service.delete_workspace(cfg, workspace_id)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )
