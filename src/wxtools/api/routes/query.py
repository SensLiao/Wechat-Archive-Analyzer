"""Query routes — search messages and retrieve context."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from wxtools.api.dependencies import get_config, verify_token
from wxtools.application import account_service, query_service
from wxtools.application.query_service import ContextRequest, QueryRequest
from wxtools.core.config import Config
from wxtools.core.errors import WxToolsError

router = APIRouter(tags=["query"], dependencies=[Depends(verify_token)])


def _status_for(code: str) -> int:
    mapping = {
        "KEY_NOT_FOUND": 401,
        "KEY_PASSWORD_WRONG": 401,
        "ACCOUNT_NOT_FOUND": 404,
        "DB_NOT_FOUND": 404,
        "CACHE_EMPTY": 404,
        "PLATFORM_NOT_SUPPORTED": 501,
    }
    return mapping.get(code, 500)


class SearchBody(BaseModel):
    keyword: Optional[str] = None
    contact: Optional[str] = None
    conversation: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    msg_type: Optional[str] = None
    limit: int = 100
    offset: int = 0
    surface: str = "chat"
    attachments: Optional[str] = None
    has_attachment: Optional[bool] = None
    sql: Optional[str] = None
    account: Optional[str] = None
    password: Optional[str] = None


class ContextBody(BaseModel):
    message_id: str
    window: int = 10
    account: Optional[str] = None
    password: Optional[str] = None


@router.post("/query")
def search(body: SearchBody, cfg: Config = Depends(get_config)) -> dict:
    """Search messages across decrypted databases."""
    try:
        reader, path = account_service.resolve_account_and_reader(
            cfg, body.account, body.password,
        )
        request = QueryRequest(
            keyword=body.keyword,
            contact=body.contact,
            conversation=body.conversation,
            since=body.since,
            until=body.until,
            msg_type=body.msg_type,
            limit=body.limit,
            offset=body.offset,
            surface=body.surface,
            attachments=body.attachments,
            sql=body.sql,
        )
        result = query_service.search(reader, path, request)

        # Post-filter: keep only messages that have an attachment
        if body.has_attachment and hasattr(result, "messages"):
            filtered = [m for m in result.messages if m.attachment_path]
            result.messages = filtered
            result.total_estimate = len(filtered)

        return result
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.post("/query/context")
def get_context(body: ContextBody, cfg: Config = Depends(get_config)) -> dict:
    """Retrieve messages surrounding a specific message."""
    try:
        reader, _path = account_service.resolve_account_and_reader(
            cfg, body.account, body.password,
        )
        request = ContextRequest(
            message_id=body.message_id,
            window=body.window,
        )
        return query_service.get_context(reader, request)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )
