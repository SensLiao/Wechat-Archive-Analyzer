"""Cross-platform directory ACL: restrict access to current user only."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def secure_dir(path: Path) -> None:
    """Create *path* (if needed) and lock it to the current user.

    Windows: sets an owner-only DACL via SetNamedSecurityInfoW.
    POSIX: chmod 0700.
    """
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        _secure_win32(path)
    else:
        os.chmod(path, 0o700)


def _secure_win32(path: Path) -> None:
    """Set owner-only ACL on Windows using win32 security APIs.

    Best-effort — silently falls back if any API call fails.
    """
    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32

    SE_FILE_OBJECT = 1
    DACL_INFO = 0x00000004 | 0x80000000  # DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION

    # Open process token to get current user SID
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)
    ):
        return

    try:
        buf_size = wintypes.DWORD(0)
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(buf_size))
        buf = ctypes.create_string_buffer(buf_size.value)
        advapi32.GetTokenInformation(token, 1, buf, buf_size, ctypes.byref(buf_size))
        sid_ptr = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
    finally:
        kernel32.CloseHandle(token)

    # Build EXPLICIT_ACCESS entry granting GENERIC_ALL to owner
    EA_SIZE = 64
    ea = ctypes.create_string_buffer(EA_SIZE)
    ctypes.memset(ea, 0, EA_SIZE)
    ctypes.cast(ea, ctypes.POINTER(ctypes.c_uint32))[0] = 0x10000000  # GENERIC_ALL
    ctypes.cast(ea, ctypes.POINTER(ctypes.c_uint32))[1] = 2  # SET_ACCESS
    ctypes.cast(ea, ctypes.POINTER(ctypes.c_uint32))[2] = 3  # SUB_CONTAINERS_AND_OBJECTS_INHERIT

    # Trustee SID pointer at offset 16+16=32
    offset = 16
    ctypes.cast(
        ctypes.addressof(ea) + offset + 16, ctypes.POINTER(ctypes.c_void_p)
    )[0] = sid_ptr

    # Create ACL from EXPLICIT_ACCESS and apply to path
    acl = ctypes.c_void_p()
    advapi32.SetEntriesInAclW(1, ea, None, ctypes.byref(acl))
    if acl:
        advapi32.SetNamedSecurityInfoW(
            str(path),
            SE_FILE_OBJECT,
            DACL_INFO,
            None,
            None,
            acl,
            None,
        )
        kernel32.LocalFree(acl)
