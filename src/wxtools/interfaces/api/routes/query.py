"""Query routes — search messages and retrieve context."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from wxtools.interfaces.api.dependencies import get_config, verify_token
from wxtools.interfaces.api.models import success_envelope
from wxtools.application import account_service, query_service
from wxtools.application.query_service import ContextRequest, QueryRequest
from wxtools.runtime.config import Config

router = APIRouter(tags=["query"], dependencies=[Depends(verify_token)])


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

    return success_envelope(result)


@router.post("/query/context")
def get_context(body: ContextBody, cfg: Config = Depends(get_config)) -> dict:
    """Retrieve messages surrounding a specific message."""
    reader, _path = account_service.resolve_account_and_reader(
        cfg, body.account, body.password,
    )
    request = ContextRequest(
        message_id=body.message_id,
        window=body.window,
    )
    return success_envelope(query_service.get_context(reader, request))
