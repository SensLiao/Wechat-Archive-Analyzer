"""Key management routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from wxtools.interfaces.api.dependencies import get_config, verify_token
from wxtools.interfaces.api.models import success_envelope
from wxtools.application import key_service
from wxtools.runtime.config import Config

router = APIRouter(tags=["key"], dependencies=[Depends(verify_token)])


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
def get_status(cfg: Config = Depends(get_config)) -> dict:
    """Return key status for all known accounts."""
    return success_envelope(key_service.get_status(cfg))


@router.post("/key/verify")
def verify_key(body: VerifyBody, cfg: Config = Depends(get_config)) -> dict:
    """Verify that the stored key can decrypt the account databases."""
    return success_envelope(key_service.verify_key(cfg, body.account, body.password))


@router.post("/key/unlock")
def unlock(body: UnlockBody, cfg: Config = Depends(get_config)) -> dict:
    """Unlock the keystore for temporary passwordless access."""
    return success_envelope(key_service.unlock(cfg, body.account, body.password, body.ttl))


@router.post("/key/lock")
def lock(body: LockBody, cfg: Config = Depends(get_config)) -> dict:
    """Lock the keystore, clearing any active unlock session."""
    return success_envelope(key_service.lock(cfg, body.account, body.clear_all))
