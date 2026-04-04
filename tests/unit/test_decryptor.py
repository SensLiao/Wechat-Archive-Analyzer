import json
import sqlite3
from pathlib import Path
from wxtools.plugins.wechat.decryptor import Decryptor, _needs_redecrypt, _parse_key_data


def test_needs_redecrypt_no_cache(tmp_path):
    src = tmp_path / "src.db"
    src.write_bytes(b"data")
    cache = tmp_path / "cache.db"
    assert _needs_redecrypt(src, cache) is True


def test_needs_redecrypt_cache_newer(tmp_path):
    import time
    src = tmp_path / "src.db"
    src.write_bytes(b"data")
    time.sleep(0.1)
    cache = tmp_path / "cache.db"
    cache.write_bytes(b"cached")
    assert _needs_redecrypt(src, cache) is False


def test_needs_redecrypt_cache_older(tmp_path):
    import time
    cache = tmp_path / "cache.db"
    cache.write_bytes(b"old")
    time.sleep(0.1)
    src = tmp_path / "src.db"
    src.write_bytes(b"new")
    assert _needs_redecrypt(src, cache) is True


def test_decryptor_init():
    d = Decryptor()
    assert isinstance(d, Decryptor)


def test_parse_key_data_json(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    keys = {"contact/contact.db": "ab" * 32}
    result = _parse_key_data(json.dumps(keys), src_dir)
    assert result == keys


def test_parse_key_data_single_hex(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.db").write_bytes(b"data")
    key_hex = "ab" * 32
    result = _parse_key_data(key_hex, src_dir)
    assert "test.db" in result
    assert result["test.db"] == key_hex
