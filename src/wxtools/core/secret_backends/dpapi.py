"""Windows DPAPI secret protection backend."""
from __future__ import annotations

import sys


class DpapiBackend:
    """Encrypt/decrypt secrets using Windows Data Protection API."""

    @property
    def name(self) -> str:
        return "windows-dpapi"

    def is_available(self) -> bool:
        return sys.platform == "win32"

    def protect(self, plaintext: bytes, *, scope: str) -> bytes:
        if not self.is_available():
            raise OSError("DPAPI is only available on Windows")
        return _dpapi_encrypt(plaintext)

    def unprotect(self, ciphertext: bytes, *, scope: str) -> bytes:
        if not self.is_available():
            raise OSError("DPAPI is only available on Windows")
        return _dpapi_decrypt(ciphertext)


def _dpapi_encrypt(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    input_blob = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    output_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)
    ):
        raise OSError("DPAPI CryptProtectData failed")
    encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
    ctypes.windll.kernel32.LocalFree(output_blob.pbData)
    return encrypted


def _dpapi_decrypt(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    input_blob = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    output_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)
    ):
        raise OSError("DPAPI CryptUnprotectData failed")
    decrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
    ctypes.windll.kernel32.LocalFree(output_blob.pbData)
    return decrypted
