import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
from wxtools.plugins.wechat.decryptor import Decryptor, _needs_redecrypt


def test_needs_redecrypt_no_cache(tmp_path):
    src = tmp_path / "src.db"
    src.write_bytes(b"data")
    cache = tmp_path / "cache.db"
    assert _needs_redecrypt(src, cache) is True


def test_needs_redecrypt_cache_newer(tmp_path):
    import os, time
    src = tmp_path / "src.db"
    src.write_bytes(b"data")
    time.sleep(0.1)
    cache = tmp_path / "cache.db"
    cache.write_bytes(b"cached")
    assert _needs_redecrypt(src, cache) is False


def test_needs_redecrypt_cache_older(tmp_path):
    import os, time
    cache = tmp_path / "cache.db"
    cache.write_bytes(b"old")
    time.sleep(0.1)
    src = tmp_path / "src.db"
    src.write_bytes(b"new")
    assert _needs_redecrypt(src, cache) is True


def test_decryptor_init():
    d = Decryptor(sqlcipher_path="sqlcipher")
    assert d._sqlcipher_path == "sqlcipher"


@patch("wxtools.plugins.wechat.decryptor.subprocess.run")
def test_decrypt_db_calls_sqlcipher(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    src = tmp_path / "encrypted.db"
    src.write_bytes(b"encrypted data")
    dest = tmp_path / "decrypted.db"

    d = Decryptor(sqlcipher_path="sqlcipher")
    tmp_dest = dest.with_suffix(".tmp")
    tmp_dest.write_bytes(b"decrypted")

    d._run_sqlcipher_decrypt(src, dest, key_hex="ab" * 32)
    assert mock_run.called
    call_args = mock_run.call_args
    assert "sqlcipher" in str(call_args)
