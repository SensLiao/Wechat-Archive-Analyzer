"""Tests for key validation via HMAC-SHA512."""
import hashlib
import hmac as hmac_mod
import struct
from wxtools.plugins.wechat.key_validator import validate_key_for_db, validate_key_for_account

PAGE_SIZE = 4096
SALT_SIZE = 16
KEY_SIZE = 32
HMAC_SIZE = 64


def _build_fake_db_page(enc_key_hex: str) -> bytes:
    """Build a fake DB page matching SQLCipher 4 layout.

    Layout: salt(16) + hmac_input(4016) + hmac(64) = 4096
    The HMAC covers page[16:4032], i.e. everything between salt and HMAC.
    """
    enc_key = bytes.fromhex(enc_key_hex)
    salt = b"\x07" * SALT_SIZE
    hmac_salt = bytes(a ^ 0x3A for a in salt)
    # hmac_input is everything between salt and HMAC: 4096 - 16 - 64 = 4016 bytes
    hmac_input = b"\x00" * (PAGE_SIZE - SALT_SIZE - HMAC_SIZE)
    hmac_key = hashlib.pbkdf2_hmac("sha512", enc_key, hmac_salt, 2, KEY_SIZE)
    h = hmac_mod.new(hmac_key, hmac_input, hashlib.sha512)
    h.update(struct.pack("<I", 1))
    hmac_value = h.digest()
    page = salt + hmac_input + hmac_value
    assert len(page) == PAGE_SIZE
    return page


def test_validate_correct_key(tmp_path):
    key_hex = "cc" * 32
    db_path = tmp_path / "message" / "message_0.db"
    db_path.parent.mkdir(parents=True)
    db_path.write_bytes(_build_fake_db_page(key_hex))
    assert validate_key_for_db(key_hex, db_path) is True


def test_validate_wrong_key(tmp_path):
    key_hex = "cc" * 32
    wrong_hex = "dd" * 32
    db_path = tmp_path / "message" / "message_0.db"
    db_path.parent.mkdir(parents=True)
    db_path.write_bytes(_build_fake_db_page(key_hex))
    assert validate_key_for_db(wrong_hex, db_path) is False


def test_validate_account_returns_report(tmp_path):
    key_hex = "ee" * 32
    db_dir = tmp_path / "db_storage"
    msg_dir = db_dir / "message"
    msg_dir.mkdir(parents=True)
    (msg_dir / "message_0.db").write_bytes(_build_fake_db_page(key_hex))
    (msg_dir / "message_1.db").write_bytes(_build_fake_db_page(key_hex))
    import json
    key_data = json.dumps({"message/message_0.db": key_hex, "message/message_1.db": key_hex})
    result = validate_key_for_account(key_data, db_dir)
    assert result["total"] == 2
    assert result["passed"] == 2
    assert result["failed"] == 0
