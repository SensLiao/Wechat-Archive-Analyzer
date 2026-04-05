"""FastAPI dependencies — config injection and session token auth."""
from __future__ import annotations

from fastapi import Header, HTTPException, Request

from wxtools.core.config import Config


def get_config(request: Request) -> Config:
    """Inject the Config instance from app state."""
    return request.app.state.cfg


def verify_token(
    request: Request,
    x_session_token: str = Header(..., alias="X-Session-Token"),
) -> None:
    """Verify the session token from request header.

    Raises 401 if token is missing or doesn't match.
    """
    expected = request.app.state.session_token
    if x_session_token != expected:
        raise HTTPException(status_code=401, detail="Invalid session token")
