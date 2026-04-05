"""Key management routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from wxtools.api.dependencies import get_config, verify_token
from wxtools.services import key_service
from wxtools.core.config import Config
from wxtools.core.errors import WxToolsError

router = APIRouter(tags=["key"], dependencies=[Depends(verify_token)])


def _status_for(code: str) -> int:
    mapping = {
        "KEY_NOT_FOUND": 401,
        "KEY_PASSWORD_WRONG": 401,
        "ACCOUNT_NOT_FOUND": 404,
        "PLATFORM_NOT_SUPPORTED": 501,
    }
    return mapping.get(code, 500)


class VerifyBody(BaseModel):
    account: Optional[str] = None
    password: Optional[str] = None


class UnlockBody(BaseModel):
    account: Optional[str] = None
    password: Optional[str] = None
    ttl: Optional[int] = None


class LockBody(BaseModel):
    account: Optional[str] = None
    clear_all: bool = False


@router.get("/key/status")
def get_status(cfg: Config = Depends(get_config)) -> list[dict]:
    """Return key status for all known accounts."""
    try:
        return key_service.get_status(cfg)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.post("/key/verify")
def verify_key(body: VerifyBody, cfg: Config = Depends(get_config)) -> dict:
    """Verify that the stored key can decrypt the account databases."""
    try:
        return key_service.verify_key(cfg, body.account, body.password)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.post("/key/unlock")
def unlock(body: UnlockBody, cfg: Config = Depends(get_config)) -> dict:
    """Unlock the keystore for temporary passwordless access."""
    try:
        return key_service.unlock(cfg, body.account, body.password, body.ttl)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )


@router.post("/key/lock")
def lock(body: LockBody, cfg: Config = Depends(get_config)) -> dict:
    """Lock the keystore, clearing any active unlock session."""
    try:
        return key_service.lock(cfg, body.account, body.clear_all)
    except WxToolsError as e:
        raise HTTPException(
            status_code=_status_for(e.code),
            detail={"code": e.code, "message": e.message, "remediation": e.remediation},
        )
