"""Extract SQLCipher key from WeChat process memory on Windows."""

from __future__ import annotations

import ctypes
import logging
import re
import sys
from typing import Callable, List, Optional, Set

import psutil

from wxtools.core.errors import AdminRequiredError, WeChatNotRunningError

logger = logging.getLogger("wxtools.key_extractor")

WECHAT_PROCESS_NAMES = {"Weixin.exe", "WeChat.exe"}
HEX_KEY_RE = re.compile(rb"[0-9a-fA-F]{64}")


def is_valid_hex_key(candidate: str) -> bool:
    if len(candidate) != 64:
        return False
    try:
        bytes.fromhex(candidate)
        return True
    except ValueError:
        return False


def extract_key_candidates_from_buffer(buffer: bytes) -> List[str]:
    matches = HEX_KEY_RE.findall(buffer)
    return list({m.decode("ascii") for m in matches})


def find_wechat_pid() -> int:
    candidates = []
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] in WECHAT_PROCESS_NAMES:
            try:
                rss = proc.memory_info().rss
                candidates.append((proc.info["pid"], rss))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                candidates.append((proc.info["pid"], 0))
    if not candidates:
        raise WeChatNotRunningError()
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def extract_key(
    pid: Optional[int] = None,
    validate_fn: Optional[Callable[[str], bool]] = None,
) -> str:
    if sys.platform != "win32":
        raise OSError("Key extraction only supported on Windows")

    if pid is None:
        pid = find_wechat_pid()

    logger.info("Scanning WeChat process PID=%d", pid)

    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    MEM_COMMIT = 0x1000
    PAGE_READWRITE = 0x04
    PAGE_READONLY = 0x02
    MEM_PRIVATE = 0x20000

    kernel32 = ctypes.windll.kernel32

    handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        raise AdminRequiredError()

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", ctypes.c_ulong),
            ("RegionSize", ctypes.c_size_t),
            ("State", ctypes.c_ulong),
            ("Protect", ctypes.c_ulong),
            ("Type", ctypes.c_ulong),
        ]

    mbi = MEMORY_BASIC_INFORMATION()
    address = 0
    all_candidates: List[str] = []

    try:
        while kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            if (
                mbi.State == MEM_COMMIT
                and mbi.Type == MEM_PRIVATE
                and mbi.Protect in (PAGE_READWRITE, PAGE_READONLY, 0x04 | 0x100, 0x02 | 0x100)
            ):
                region_size = mbi.RegionSize
                if region_size > 0 and region_size < 100 * 1024 * 1024:
                    buffer = ctypes.create_string_buffer(region_size)
                    bytes_read = ctypes.c_size_t(0)
                    if kernel32.ReadProcessMemory(
                        handle, ctypes.c_void_p(mbi.BaseAddress), buffer, region_size, ctypes.byref(bytes_read)
                    ):
                        candidates = extract_key_candidates_from_buffer(buffer.raw[: bytes_read.value])
                        all_candidates.extend(candidates)

            address = mbi.BaseAddress + mbi.RegionSize
            if address <= mbi.BaseAddress:
                break
    finally:
        kernel32.CloseHandle(handle)

    unique = list(dict.fromkeys(all_candidates))
    logger.info("Found %d unique key candidates", len(unique))

    if validate_fn:
        for candidate in unique:
            if validate_fn(candidate):
                logger.info("Valid key found")
                return candidate
        raise RuntimeError("No valid key found among candidates. WeChat version may not be supported.")

    if unique:
        return unique[0]

    raise RuntimeError("No key candidates found in WeChat process memory.")
