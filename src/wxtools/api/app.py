"""FastAPI application factory for the local Web API."""
from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from wxtools.core.config import load_config


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

    # CORS — only allow localhost origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:*", "http://localhost:*"],
        allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from wxtools.api.routes import accounts, cache, export, home, key, query, workspaces

    app.include_router(accounts.router, prefix="/api")
    app.include_router(key.router, prefix="/api")
    app.include_router(home.router, prefix="/api")
    app.include_router(query.router, prefix="/api")
    app.include_router(workspaces.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    app.include_router(cache.router, prefix="/api")

    # Health check (no auth required)
    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.5.0"}

    # Serve static frontend files if directory provided
    if static_dir and static_dir.is_dir():
        app.mount(
            "/", StaticFiles(directory=str(static_dir), html=True), name="static"
        )

    return app, token
