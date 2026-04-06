"""Cache management routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from wxtools.interfaces.api.dependencies import get_config, verify_token
from wxtools.interfaces.api.models import success_envelope
from wxtools.application import cache_service
from wxtools.runtime.config import Config

router = APIRouter(tags=["cache"], dependencies=[Depends(verify_token)])


class CacheAccountBody(BaseModel):
    account: Optional[str] = None


@router.get("/cache/status")
def get_status(cfg: Config = Depends(get_config)) -> dict:
    """Return cache status including size and account breakdown."""
    return success_envelope(cache_service.get_status(cfg))


@router.post("/cache/clear")
def clear_cache(
    body: CacheAccountBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Clear the decrypted cache."""
    return success_envelope(cache_service.clear_cache(cfg, body.account))


@router.post("/cache/build-index")
def build_index(
    body: CacheAccountBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Build or rebuild the FTS search index."""
    return success_envelope(cache_service.build_index(cfg, body.account))


@router.post("/cache/drop-index")
def drop_index(
    body: CacheAccountBody,
    cfg: Config = Depends(get_config),
) -> dict:
    """Drop the FTS search index."""
    return success_envelope(cache_service.drop_index(cfg, body.account))
