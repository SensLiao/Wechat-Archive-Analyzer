"""Account routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from wxtools.interfaces.api.dependencies import get_config, verify_token
from wxtools.interfaces.api.models import success_envelope
from wxtools.application import account_service
from wxtools.runtime.config import Config

router = APIRouter(tags=["accounts"], dependencies=[Depends(verify_token)])


@router.get("/accounts")
def list_accounts(cfg: Config = Depends(get_config)) -> dict:
    """List all discovered WeChat accounts."""
    return success_envelope(account_service.list_accounts(cfg))
