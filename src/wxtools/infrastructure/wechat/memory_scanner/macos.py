"""macOS memory scanner using Mach VM APIs."""
from __future__ import annotations

import ctypes
import ctypes.util
from typing import Iterator, Optional

from wxtools.domain.errors import AdminRequiredError

# Mach kernel constants
KERN_SUCCESS = 0
VM_REGION_BASIC_INFO_64 = 9
VM_PROT_READ = 0x01


class _VMRegionBasicInfo64(ctypes.Structure):
    _fields_ = [
        ("protection", ctypes.c_int32),
        ("max_protection", ctypes.c_int32),
        ("inheritance", ctypes.c_uint32),
        ("shared", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("offset", ctypes.c_uint64),
        ("behavior", ctypes.c_int32),
        ("user_wired_count", ctypes.c_uint16),
    ]


def _load_libc() -> ctypes.CDLL:
    path = ctypes.util.find_library("c")
    if not path:
        raise OSError("Cannot find libc")
    return ctypes.CDLL(path)


class MacosMemoryScanner:
    """task_for_pid + mach_vm_read implementation."""

    def __init__(self) -> None:
        self._task: Optional[int] = None
        self._libc: Optional[ctypes.CDLL] = None

    def open(self, pid: int) -> None:
        libc = _load_libc()
        self._libc = libc
        task = ctypes.c_uint32()
        kr = libc.task_for_pid(libc.mach_task_self(), pid, ctypes.byref(task))
        if kr != KERN_SUCCESS:
            raise AdminRequiredError(
                "Failed to attach to WeChat process. "
                "Run with sudo or grant debugger entitlement."
            )
        self._task = task.value

    def close(self) -> None:
        if self._task is not None and self._libc is not None:
            self._libc.mach_port_deallocate(self._libc.mach_task_self(), self._task)
            self._task = None

    def readable_regions(self) -> Iterator[bytes]:
        address = ctypes.c_uint64(0)
        size = ctypes.c_uint64(0)
        info = _VMRegionBasicInfo64()
        count = ctypes.c_uint32(ctypes.sizeof(info) // 4)
        obj_name = ctypes.c_uint32(0)

        while True:
            count.value = ctypes.sizeof(info) // 4
            kr = self._libc.mach_vm_region(
                self._task,
                ctypes.byref(address),
                ctypes.byref(size),
                VM_REGION_BASIC_INFO_64,
                ctypes.byref(info),
                ctypes.byref(count),
                ctypes.byref(obj_name),
            )
            if kr != KERN_SUCCESS:
                break

            region_size = size.value
            if (info.protection & VM_PROT_READ) and 0 < region_size < 200 * 1024 * 1024:
                data = self._read_region(address.value, region_size)
                if data is not None:
                    yield data

            address.value += region_size

    def _read_region(self, addr: int, size: int) -> Optional[bytes]:
        data_ptr = ctypes.c_void_p()
        data_cnt = ctypes.c_uint32()
        kr = self._libc.mach_vm_read(
            self._task,
            ctypes.c_uint64(addr),
            ctypes.c_uint64(size),
            ctypes.byref(data_ptr),
            ctypes.byref(data_cnt),
        )
        if kr != KERN_SUCCESS:
            return None
        try:
            return ctypes.string_at(data_ptr.value, data_cnt.value)
        finally:
            self._libc.mach_vm_deallocate(
                self._libc.mach_task_self(), data_ptr, data_cnt
            )

    def read_pointer(self, addr: int, size: int) -> Optional[bytes]:
        return self._read_region(addr, size)

    def __enter__(self) -> MacosMemoryScanner:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
