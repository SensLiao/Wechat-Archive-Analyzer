"""Export routes — export messages and list templates."""
from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from wxtools.interfaces.api.dependencies import get_config, verify_token
from wxtools.interfaces.api.models import success_envelope
from wxtools.application import account_service, export_service
from wxtools.application.export_service import ExportRequest
from wxtools.runtime.config import Config

logger = logging.getLogger("wxtools.api.export")

router = APIRouter(tags=["export"], dependencies=[Depends(verify_token)])

# Separate router for browser-initiated downloads (token via query param, not header)
download_router = APIRouter(tags=["export"])

AVAILABLE_TEMPLATES = [
    {"id": "json", "name": "json", "description": "JSON export (default)"},
    {"id": "csv", "name": "csv", "description": "CSV spreadsheet export"},
    {"id": "html", "name": "html", "description": "HTML readable export"},
]

# In-memory registry of downloadable exports (cleared on server restart)
_pending_downloads: dict[str, Path] = {}

# Max pending downloads to avoid unbounded memory / disk growth
_MAX_PENDING = 50


def _cleanup_oldest() -> None:
    """Remove the oldest pending download if we've exceeded the limit."""
    while len(_pending_downloads) > _MAX_PENDING:
        oldest_id = next(iter(_pending_downloads))
        old_path = _pending_downloads.pop(oldest_id)
        if old_path.exists():
            if old_path.is_dir():
                shutil.rmtree(old_path, ignore_errors=True)
            else:
                old_path.unlink(missing_ok=True)
        logger.debug("Cleaned up old export: %s", oldest_id)


class RunExportBody(BaseModel):
    format: str = "json"
    output_dir: Optional[str] = None
    contact: Optional[str] = None
    conversation: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: Optional[int] = None
    surface: str = "chat"
    attachments: Optional[str] = None
    template: Optional[str] = None
    account: Optional[str] = None
    password: Optional[str] = None


@router.get("/export/templates")
def list_templates() -> dict:
    """Return the list of available export templates."""
    return success_envelope({"templates": AVAILABLE_TEMPLATES})


@router.post("/export")
def run_export(body: RunExportBody, cfg: Config = Depends(get_config)) -> dict:
    """Run a full message export.

    When *output_dir* is omitted (the default for the Web UI), the export
    is written to a temporary directory and a ``download_id`` is returned.
    The frontend can then trigger a browser download via
    ``GET /export/download/{download_id}``.

    When *output_dir* is explicitly provided (e.g. from the CLI), files
    are written there directly and no ``download_id`` is issued.
    """
    reader, path = account_service.resolve_account_and_reader(
        cfg, body.account, body.password,
    )

    # Decide output location
    browser_download = body.output_dir is None
    if browser_download:
        tmp = Path(tempfile.mkdtemp(prefix="wxtools-export-"))
        effective_output = str(tmp)
    else:
        effective_output = body.output_dir  # type: ignore[assignment]

    request = ExportRequest(
        format=body.format,
        output_dir=effective_output,
        contact=body.contact,
        conversation=body.conversation,
        since=body.since,
        until=body.until,
        limit=body.limit,
        surface=body.surface,
        attachments=body.attachments,
        template=body.template,
    )
    result = export_service.run_export(reader, path, request)

    response_data: dict = {
        "total_messages": result.total_messages,
        "total_conversations": result.total_conversations,
        "files": result.files,
        "output_dir": result.output_dir,
        "format": result.format,
    }

    # For browser downloads, zip the output and register for download
    if browser_download:
        export_dir = Path(result.output_dir)
        download_id = uuid.uuid4().hex[:12]

        # Create a zip archive next to the temp dir
        zip_stem = f"wxtools-export-{download_id}"
        zip_path = Path(tempfile.gettempdir()) / f"{zip_stem}.zip"
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", str(export_dir))

        # Clean up the unzipped temp dir
        shutil.rmtree(export_dir, ignore_errors=True)

        _pending_downloads[download_id] = zip_path
        _cleanup_oldest()

        response_data["download_id"] = download_id
        logger.info("Export ready for download: %s (%s)", download_id, zip_path)

    return success_envelope(response_data)


@download_router.get("/export/download/{download_id}")
def download_export(download_id: str, request: Request) -> FileResponse:
    """Serve a previously exported zip file as a browser download.

    Token is passed as a query parameter since this is opened directly
    by the browser (not via fetch).
    """
    # Verify token from query param (browser navigates here directly)
    token = request.query_params.get("token", "")
    expected = request.app.state.session_token
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid session token")

    zip_path = _pending_downloads.get(download_id)
    if zip_path is None or not zip_path.exists():
        raise HTTPException(status_code=404, detail="Export not found or expired")

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"wxtools-export-{download_id}.zip",
    )
