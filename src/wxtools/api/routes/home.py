"""Home / dashboard routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from wxtools.api.dependencies import get_config, verify_token
from wxtools.services import home_service
from wxtools.core.config import Config
from wxtools.core.errors import WxToolsError

router = APIRouter(tags=["home"], dependencies=[Depends(verify_token)])


def _status_for(code: str) -> int:
    mapping = {
        "ACCOUNT_NOT_FOUND": 404,
        "PLATFORM_NOT_SUPPORTED": 501,
    }
    return mapping.get(code, 500)


@router.get("/home/summary")
def get_summary(cfg: Config = Depends(get_config)) -> dict:
    """Return a high-level summary for the dashboard."""
    try:
        return home_service.get_summary(cfg)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )
