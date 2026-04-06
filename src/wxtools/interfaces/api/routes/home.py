"""Home / dashboard routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from wxtools.interfaces.api.dependencies import get_config, verify_token
from wxtools.interfaces.api.models import success_envelope
from wxtools.application import home_service
from wxtools.runtime.config import Config

router = APIRouter(tags=["home"], dependencies=[Depends(verify_token)])


@router.get("/home/summary")
def get_summary(cfg: Config = Depends(get_config)) -> dict:
    """Return a high-level summary for the dashboard."""
    return success_envelope(home_service.get_summary(cfg))
