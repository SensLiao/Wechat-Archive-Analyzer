"""Base protocol for platform-specific process memory scanning."""
from __future__ import annotations

from typing import Iterator, Optional, Protocol


class MemoryScanner(Protocol):
    """Yields readable memory regions from a target process."""

    def open(self, pid: int) -> None:
        """Attach to process. Raises AdminRequiredError on permission failure."""
        ...

    def close(self) -> None:
        """Detach / release handle."""
        ...

    def readable_regions(self) -> Iterator[bytes]:
        """Yield each readable memory region as bytes."""
        ...

    def read_pointer(self, addr: int, size: int) -> Optional[bytes]:
        """Read `size` bytes at `addr`. Return None on failure."""
        ...

    def __enter__(self) -> MemoryScanner:
        ...

    def __exit__(self, *exc: object) -> None:
        ...
