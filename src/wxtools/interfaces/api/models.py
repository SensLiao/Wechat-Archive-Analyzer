"""Unified API response models.

All API endpoints return an ``ApiEnvelope`` wrapper that provides a
consistent shape for both success and error responses.
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Error detail
# ---------------------------------------------------------------------------

class ApiErrorDetail(BaseModel):
    """Machine-readable error information."""

    code: str
    message: str
    remediation: Optional[str] = None


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------

class ApiEnvelope(BaseModel, Generic[T]):
    """Standard response wrapper for every API endpoint.

    On success: ``ok=True``, ``data=<payload>``, ``error=None``.
    On failure: ``ok=False``, ``data=None``, ``error=<ApiErrorDetail>``.
    """

    ok: bool
    data: Optional[T] = None
    error: Optional[ApiErrorDetail] = None


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

class AccountSummary(BaseModel):
    discovered: List[str] = Field(default_factory=list)
    count: int = 0
    active: Optional[str] = None


class KeySummary(BaseModel):
    stored: int = 0
    verified: int = 0
    accounts: List[str] = Field(default_factory=list)


class CacheSummary(BaseModel):
    exists: bool = False
    size_bytes: int = 0
    size_human: str = ""
    account_count: int = 0


class HomeSummaryData(BaseModel):
    accounts: AccountSummary
    keys: KeySummary
    cache: CacheSummary
    recent_searches: List[Any] = Field(default_factory=list)
    recent_exports: List[Any] = Field(default_factory=list)
    recent_workspaces: List[Any] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class AccountInfo(BaseModel):
    wxid: str
    db_dir: Optional[str] = None
    path: Optional[str] = None

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Key
# ---------------------------------------------------------------------------

class KeyStatusItem(BaseModel):
    wxid: str = ""
    plugin: str = ""
    protection: str = ""
    created_at: str = ""
    last_verified: str = ""


class KeyVerifyData(BaseModel):
    account: str
    total: Optional[int] = None
    passed: Optional[int] = None
    failed: Optional[int] = None
    details: Optional[List[Any]] = None

    model_config = {"extra": "allow"}


class KeyUnlockData(BaseModel):
    account: str
    status: str
    ttl_minutes: Optional[int] = None


class KeyLockData(BaseModel):
    status: str
    account: Optional[str] = None


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class CacheAccountInfo(BaseModel):
    wxid: str
    path: str
    size_bytes: int
    size_human: str
    db_count: int
    decrypted_at: Optional[str] = None


class CacheStatusData(BaseModel):
    cache_dir: str
    accounts: List[CacheAccountInfo] = Field(default_factory=list)
    total_size_bytes: int = 0
    total_size_human: str = ""


class CacheClearData(BaseModel):
    cleared: str
    freed_bytes: int = 0


class CacheIndexData(BaseModel):
    account: str
    indexed: Optional[int] = None
    dropped: Optional[bool] = None


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class MessageData(BaseModel):
    """A single message — allows extra fields from the schema."""

    model_config = {"extra": "allow"}

    id: Optional[str] = None
    server_id: Optional[int] = None
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    is_self: Optional[bool] = None
    timestamp: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None
    raw_type: Optional[int] = None
    raw_sub_type: Optional[int] = None
    attachment_path: Optional[str] = None
    source_db: Optional[str] = None
    surface: Optional[str] = None
    attachment_exists: Optional[bool] = None


class QueryResultData(BaseModel):
    messages: List[Any] = Field(default_factory=list)
    total_estimate: int = 0
    has_more: bool = False
    query: Optional[Any] = None

    model_config = {"extra": "allow"}


class ContextResultData(BaseModel):
    target: Optional[Any] = None
    before: List[Any] = Field(default_factory=list)
    after: List[Any] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class ExportTemplateInfo(BaseModel):
    id: str
    name: str
    description: str


class ExportTemplatesData(BaseModel):
    templates: List[ExportTemplateInfo]


class ExportResultData(BaseModel):
    total_messages: int = 0
    total_conversations: int = 0
    files: List[Any] = Field(default_factory=list)
    output_dir: str = ""
    format: str = ""


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------

class WorkspaceSummary(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    item_count: int = 0


class WorkspaceData(BaseModel):
    """Full workspace including items."""

    id: str
    name: str = ""
    description: Optional[str] = ""
    created_at: str = ""
    updated_at: str = ""
    items: List[Any] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class WorkspaceDeleteData(BaseModel):
    id: str
    deleted: bool


class WorkspaceItemData(BaseModel):
    """A single workspace item — allows extra fields."""

    model_config = {"extra": "allow"}

    id: Optional[str] = None
    type: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

class OnboardingStatusData(BaseModel):
    current_step: str
    wechat_installed: bool
    data_dir_found: bool
    data_dir: Optional[str] = None
    accounts_found: List[Any] = Field(default_factory=list)
    keys_available: List[str] = Field(default_factory=list)
    keys_missing: List[str] = Field(default_factory=list)
    decryption_verified: bool
    is_complete: bool
    message: str


class OnboardingExtractData(BaseModel):
    account: str
    protection: str = ""
    status: str
    db_count: int = 0

    model_config = {"extra": "allow"}


class OnboardingVerifyData(BaseModel):
    account: str
    total: Optional[int] = None
    passed: Optional[int] = None
    failed: Optional[int] = None
    details: Optional[List[Any]] = None

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Helper to build envelopes
# ---------------------------------------------------------------------------

def success_envelope(data: Any) -> dict:
    """Build a success envelope dict (FastAPI will serialize it)."""
    return {"ok": True, "data": data, "error": None}


def error_envelope(code: str, message: str, remediation: str | None = None) -> dict:
    """Build an error envelope dict."""
    return {
        "ok": False,
        "data": None,
        "error": {"code": code, "message": message, "remediation": remediation},
    }
