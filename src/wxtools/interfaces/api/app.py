"""FastAPI application factory for the local Web API."""
from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from wxtools.domain.errors import WxToolsError
from wxtools.interfaces.api.models import error_envelope, success_envelope
from wxtools.runtime.config import load_config

logger = logging.getLogger("wxtools.api")

# HTTP status mapping for known error codes
_ERROR_STATUS: dict[str, int] = {
    "KEY_NOT_FOUND": 404,
    "KEY_PASSWORD_WRONG": 403,
    "ACCOUNT_NOT_FOUND": 404,
    "DB_NOT_FOUND": 404,
    "CACHE_EMPTY": 404,
    "WORKSPACE_NOT_FOUND": 404,
    "WORKSPACE_ITEM_NOT_FOUND": 404,
    "PLATFORM_NOT_SUPPORTED": 501,
}


def create_app(*, static_dir: Path | None = None) -> tuple[FastAPI, str]:
    """Create and configure the FastAPI application.

    Generates a random session token at startup. All routes require this
    token via the X-Session-Token header (enforced in dependencies).

    Returns:
        Tuple of (app, token) so the CLI startup command can display
        the token to the user.
    """
    cfg = load_config()
    token = secrets.token_urlsafe(32)

    app = FastAPI(
        title="wxtools Local API",
        version="0.5.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Store config and token in app state for dependency injection
    app.state.cfg = cfg
    app.state.session_token = token

    # ---- Global exception handler for WxToolsError --------------------------
    @app.exception_handler(WxToolsError)
    async def wxtools_error_handler(request: Request, exc: WxToolsError) -> JSONResponse:
        status = _ERROR_STATUS.get(exc.code, 500)
        return JSONResponse(
            status_code=status,
            content=error_envelope(exc.code, exc.message, exc.remediation),
        )

    # ---- Catch-all for unexpected errors ------------------------------------
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=error_envelope("INTERNAL_ERROR", str(exc)),
        )

    # CORS — only allow localhost origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:*", "http://localhost:*"],
        allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from wxtools.interfaces.api.routes import accounts, cache, export, home, key, onboarding, query, workspaces

    app.include_router(accounts.router, prefix="/api")
    app.include_router(key.router, prefix="/api")
    app.include_router(home.router, prefix="/api")
    app.include_router(onboarding.router, prefix="/api")
    app.include_router(query.router, prefix="/api")
    app.include_router(workspaces.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    app.include_router(cache.router, prefix="/api")

    # Health check (no auth required)
    @app.get("/api/health")
    async def health():
        return success_envelope({"status": "ok", "version": "0.5.0"})

    # Serve static frontend files if directory provided
    if static_dir and static_dir.is_dir():
        app.mount(
            "/", StaticFiles(directory=str(static_dir), html=True), name="static"
        )

    return app, token
