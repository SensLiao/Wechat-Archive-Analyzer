"""Export routes — export messages and list templates."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from wxtools.api.dependencies import get_config, verify_token
from wxtools.application import account_service, export_service
from wxtools.application.export_service import ExportRequest
from wxtools.core.config import Config
from wxtools.core.errors import WxToolsError

router = APIRouter(tags=["export"], dependencies=[Depends(verify_token)])

AVAILABLE_TEMPLATES = [
    {"id": "json", "name": "json", "description": "JSON export (default)"},
    {"id": "csv", "name": "csv", "description": "CSV spreadsheet export"},
    {"id": "html", "name": "html", "description": "HTML readable export"},
]


def _status_for(code: str) -> int:
    mapping = {
        "KEY_NOT_FOUND": 401,
        "KEY_PASSWORD_WRONG": 401,
        "ACCOUNT_NOT_FOUND": 404,
        "DB_NOT_FOUND": 404,
        "PLATFORM_NOT_SUPPORTED": 501,
    }
    return mapping.get(code, 500)


class RunExportBody(BaseModel):
    format: str = "json"
    output_dir: str = "."
    contact: Optional[str] = None
    conversation: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: Optional[int] = None
    surface: str = "chat"
    attachments: Optional[str] = None
    template: Optional[str] = None
    account: Optional[str] = None
    password: Optional[str] = None


@router.get("/export/templates")
def list_templates() -> dict:
    """Return the list of available export templates."""
    return {"templates": AVAILABLE_TEMPLATES}


@router.post("/export")
def run_export(body: RunExportBody, cfg: Config = Depends(get_config)) -> dict:
    """Run a full message export."""
    try:
        reader, path = account_service.resolve_account_and_reader(
            cfg, body.account, body.password,
        )
        request = ExportRequest(
            format=body.format,
            output_dir=body.output_dir,
            contact=body.contact,
            conversation=body.conversation,
            since=body.since,
            until=body.until,
            limit=body.limit,
            surface=body.surface,
            attachments=body.attachments,
            template=body.template,
        )
        result = export_service.run_export(reader, path, request)
        return {
            "total_messages": result.total_messages,
            "total_conversations": result.total_conversations,
            "files": result.files,
            "output_dir": result.output_dir,
            "format": result.format,
        }
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )
