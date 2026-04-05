"""Cache management routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from wxtools.api.dependencies import get_config, verify_token
from wxtools.application import cache_service
from wxtools.core.config import Config
from wxtools.core.errors import WxToolsError

router = APIRouter(tags=["cache"], dependencies=[Depends(verify_token)])


def _status_for(code: str) -> int:
    mapping = {
        "CACHE_EMPTY": 404,
        "ACCOUNT_NOT_FOUND": 404,
        "PLATFORM_NOT_SUPPORTED": 501,
    }
    return mapping.get(code, 500)


class CacheAccountBody(BaseModel):
    account: Optional[str] = None


@router.get("/cache/status")
def get_status(cfg: Config = Depends(get_config)) -> dict:
    """Return cache status including size and account breakdown."""
    try:
        return cache_service.get_status(cfg)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.post("/cache/clear")
def clear_cache(
    body: CacheAccountBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Clear the decrypted cache."""
    try:
        return cache_service.clear_cache(cfg, body.account)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.post("/cache/build-index")
def build_index(
    body: CacheAccountBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Build or rebuild the FTS search index."""
    try:
        return cache_service.build_index(cfg, body.account)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.post("/cache/drop-index")
def drop_index(
    body: CacheAccountBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Drop the FTS search index."""
    try:
        return cache_service.drop_index(cfg, body.account)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )
