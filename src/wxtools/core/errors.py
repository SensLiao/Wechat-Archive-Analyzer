"""Structured error hierarchy for wxtools CLI."""


class WxToolsError(Exception):
    """Base error with machine-readable code and remediation hint."""

    def __init__(self, code: str, message: str, remediation: str):
        super().__init__(message)
        self.code = code
        self.message = message
        self.remediation = remediation

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
        }


class KeyNotFoundError(WxToolsError):
    def __init__(self, account: str = ""):
        msg = f"No cached key found for account '{account}'." if account else "No cached key found."
        super().__init__("KEY_NOT_FOUND", msg, "Run 'wxtools key extract' with admin privileges while WeChat is running.")


class KeyInvalidError(WxToolsError):
    def __init__(self):
        super().__init__("KEY_INVALID", "Cached key failed validation.", "Re-extract with 'wxtools key extract'.")


class KeyPasswordWrongError(WxToolsError):
    def __init__(self):
        super().__init__("KEY_PASSWORD_WRONG", "Wrong password for keystore.", "Retry with the correct password.")


class WeChatNotRunningError(WxToolsError):
    def __init__(self):
        super().__init__("WECHAT_NOT_RUNNING", "WeChat process not found.", "Start WeChat and log in first.")


class AdminRequiredError(WxToolsError):
    def __init__(self):
        super().__init__("ADMIN_REQUIRED", "Administrator privileges required.", "Run terminal as Administrator.")


class DbNotFoundError(WxToolsError):
    def __init__(self, path: str = ""):
        super().__init__("DB_NOT_FOUND", f"Database not found: {path}", "Check WeChat data path in config.")


class DbLockedError(WxToolsError):
    def __init__(self):
        super().__init__("DB_LOCKED", "Database locked by WeChat.", "Retry, or close WeChat temporarily.")


class DbDecryptFailedError(WxToolsError):
    def __init__(self):
        super().__init__("DB_DECRYPT_FAILED", "Decryption failed.", "Re-extract key with 'wxtools key extract'.")


class CacheEmptyError(WxToolsError):
    def __init__(self):
        super().__init__("CACHE_EMPTY", "No decrypted cache found.", "Run a query first to trigger decryption.")


class AmbiguousContactError(WxToolsError):
    def __init__(self, name: str, candidates: list):
        super().__init__(
            "AMBIGUOUS_CONTACT",
            f"Multiple contacts match '{name}'.",
            "Use a more specific name or remark.",
        )
        self.candidates = candidates

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["candidates"] = self.candidates
        return d


class AmbiguousConversationError(WxToolsError):
    def __init__(self, name: str, candidates: list):
        super().__init__(
            "AMBIGUOUS_CONVERSATION",
            f"Multiple conversations match '{name}'.",
            "Use a more specific name.",
        )
        self.candidates = candidates

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["candidates"] = self.candidates
        return d


class NoResultsError(WxToolsError):
    def __init__(self):
        super().__init__("NO_RESULTS", "Query returned no results.", "Try adjusting your search filters.")


class SqlError(WxToolsError):
    def __init__(self, detail: str = ""):
        super().__init__("SQL_ERROR", f"SQL error: {detail}", "Check SQL syntax.")


class ConfigError(WxToolsError):
    def __init__(self, detail: str = ""):
        super().__init__("CONFIG_ERROR", f"Configuration error: {detail}", "Check ~/.wxtools/config.yaml.")


class AccountNotFoundError(WxToolsError):
    def __init__(self, wxid: str = ""):
        super().__init__("ACCOUNT_NOT_FOUND", f"Account not found: {wxid}", "Check available accounts with 'wxtools key status'.")


class ExportConfirmRequiredError(WxToolsError):
    def __init__(self, estimated_count: int):
        super().__init__(
            "EXPORT_CONFIRM_REQUIRED",
            f"Large export: ~{estimated_count} messages. Use --yes to confirm.",
            "Add --yes flag to proceed.",
        )
        self.estimated_count = estimated_count
