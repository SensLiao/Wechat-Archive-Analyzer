"""Windows memory scanner using kernel32 APIs."""
from __future__ import annotations

import ctypes
from typing import Iterator, Optional

from wxtools.core.errors import AdminRequiredError


class _MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_ulonglong),
        ("AllocationBase", ctypes.c_ulonglong),
        ("AllocationProtect", ctypes.c_ulong),
        ("PartitionId", ctypes.c_ushort),
        ("_a1", ctypes.c_ushort),
        ("RegionSize", ctypes.c_ulonglong),
        ("State", ctypes.c_ulong),
        ("Protect", ctypes.c_ulong),
        ("Type", ctypes.c_ulong),
        ("_a2", ctypes.c_ulong),
    ]


class WindowsMemoryScanner:
    """ReadProcessMemory + VirtualQueryEx implementation."""

    def __init__(self) -> None:
        self._handle: Optional[int] = None
        self._kernel32 = None

    def open(self, pid: int) -> None:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(0x0410, False, pid)
        if not handle:
            raise AdminRequiredError()
        self._kernel32 = kernel32
        self._handle = handle

    def close(self) -> None:
        if self._handle:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None

    def readable_regions(self) -> Iterator[bytes]:
        mbi = _MBI()
        addr = 0
        while addr < 0x7FFFFFFFFFFFFFFF:
            if self._kernel32.VirtualQueryEx(
                self._handle,
                ctypes.c_void_p(addr),
                ctypes.byref(mbi),
                ctypes.sizeof(mbi),
            ) == 0:
                break
            base = mbi.BaseAddress or 0
            size = mbi.RegionSize or 0
            if (
                mbi.State == 0x1000  # MEM_COMMIT
                and mbi.Protect not in (0x01, 0x100)  # not NOACCESS / GUARD
                and 0 < size < 200 * 1024 * 1024
            ):
                buf = ctypes.create_string_buffer(size)
                br = ctypes.c_size_t(0)
                if self._kernel32.ReadProcessMemory(
                    self._handle, ctypes.c_void_p(base), buf, size, ctypes.byref(br)
                ):
                    yield buf.raw[: br.value]
            na = base + size
            if na <= addr:
                break
            addr = na

    def read_pointer(self, addr: int, size: int) -> Optional[bytes]:
        buf = ctypes.create_string_buffer(size)
        if self._kernel32.ReadProcessMemory(
            self._handle, ctypes.c_void_p(addr), buf, size, 0
        ):
            return bytes(buf)
        return None

    def __enter__(self) -> WindowsMemoryScanner:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
