"""Tests for cache metadata written by Decryptor."""
import json
from pathlib import Path
import pytest


def _make_encrypted_db(path: Path, key_hex: str) -> None:
    """Create a minimal fake encrypted DB for testing decryptor flow."""
    import hashlib
    import hmac as hmac_mod
    import struct
    from Crypto.Cipher import AES

    PAGE_SIZE = 4096
    SALT_SIZE = 16
    KEY_SIZE = 32
    RESERVE_SIZE = 80

    enc_key = bytes.fromhex(key_hex)
    salt = b"\x01" * SALT_SIZE
    hmac_salt = bytes(a ^ 0x3A for a in salt)

    header = b"SQLite format 3\x00"
    content = header + b"\x00" * (PAGE_SIZE - SALT_SIZE - RESERVE_SIZE - len(header))

    hmac_key = hashlib.pbkdf2_hmac("sha512", enc_key, hmac_salt, 2, KEY_SIZE)

    iv = b"\x00" * 16
    cipher = AES.new(enc_key, AES.MODE_CBC, iv)
    encrypted_content = cipher.encrypt(content)

    hmac_input = encrypted_content
    h = hmac_mod.new(hmac_key, hmac_input, hashlib.sha512)
    h.update(struct.pack("<I", 1))
    hmac_value = h.digest()

    padding_size = RESERVE_SIZE - 16 - 64
    page = salt + encrypted_content + iv + hmac_value + b"\x00" * padding_size

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(page)


def test_decrypt_all_writes_cache_meta(tmp_path):
    from wxtools.plugins.wechat.decryptor import Decryptor

    key_hex = "ab" * 32
    source_dir = tmp_path / "source" / "message"
    source_dir.mkdir(parents=True)
    _make_encrypted_db(source_dir / "message_0.db", key_hex)

    cache_dir = tmp_path / "cache"
    d = Decryptor()
    key_data = json.dumps({"message/message_0.db": key_hex})
    d.decrypt_all(tmp_path / "source", cache_dir, key_data)

    meta_path = cache_dir / ".cache_meta.json"
    assert meta_path.exists(), ".cache_meta.json should be written after decrypt"
    meta = json.loads(meta_path.read_text("utf-8"))
    assert meta["version"] == 1
    assert len(meta["databases"]) == 1
    assert meta["databases"][0]["source"] == "message/message_0.db"
    assert "source_mtime" in meta["databases"][0]
    assert "size_bytes" in meta["databases"][0]
    assert "decrypted_at" in meta["databases"][0]
