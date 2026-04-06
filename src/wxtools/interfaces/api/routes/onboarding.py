"""Onboarding routes — first-run detection and setup."""
from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from wxtools.interfaces.api.dependencies import get_config, verify_token
from wxtools.interfaces.api.models import success_envelope
from wxtools.runtime.config import Config

router = APIRouter(tags=["onboarding"], dependencies=[Depends(verify_token)])


class ExtractKeyBody(BaseModel):
    account: Optional[str] = None
    password: Optional[str] = None


class VerifyBody(BaseModel):
    account: Optional[str] = None
    password: Optional[str] = None


@router.get("/onboarding/status")
def get_onboarding_status(cfg: Config = Depends(get_config)) -> dict:
    """Return the current onboarding status."""
    from wxtools.application import onboarding_service

    status = onboarding_service.check_onboarding_status(cfg)
    data = asdict(status)
    data["current_step"] = status.current_step.value
    return success_envelope(data)


@router.post("/onboarding/extract-key")
def extract_key(body: ExtractKeyBody, cfg: Config = Depends(get_config)) -> dict:
    """Trigger key extraction for a specific account."""
    from wxtools.application import key_service

    result = key_service.extract_key(
        cfg, wxid=body.account, password=body.password,
    )
    return success_envelope(result)


@router.post("/onboarding/verify")
def verify(body: VerifyBody, cfg: Config = Depends(get_config)) -> dict:
    """Verify that the stored key can decrypt databases."""
    from wxtools.application import key_service

    result = key_service.verify_key(cfg, body.account, body.password)
    return success_envelope(result)
