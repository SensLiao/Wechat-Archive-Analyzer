"""Tests for key verify and key set CLI commands."""
import hashlib
import hmac as hmac_mod
import json
import struct
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
from wxtools.cli.main import cli

PAGE_SIZE = 4096
SALT_SIZE = 16
KEY_SIZE = 32
RESERVE_SIZE = 80


def _build_fake_db_page(enc_key_hex: str) -> bytes:
    from Crypto.Cipher import AES
    enc_key = bytes.fromhex(enc_key_hex)
    salt = b"\x07" * SALT_SIZE
    hmac_salt = bytes(a ^ 0x3A for a in salt)
    content = b"\x00" * (PAGE_SIZE - SALT_SIZE - RESERVE_SIZE)
    iv = b"\x00" * 16
    cipher = AES.new(enc_key, AES.MODE_CBC, iv)
    encrypted_content = cipher.encrypt(content)
    hmac_key = hashlib.pbkdf2_hmac("sha512", enc_key, hmac_salt, 2, KEY_SIZE)
    h = hmac_mod.new(hmac_key, encrypted_content, hashlib.sha512)
    h.update(struct.pack("<I", 1))
    hmac_value = h.digest()
    padding_size = RESERVE_SIZE - 16 - 64
    page = salt + encrypted_content + iv + hmac_value + b"\x00" * padding_size
    return page


def _setup_fake_account(tmp_path, key_hex="cc" * 32):
    """Create fake DB files and a keystore with a stored key."""
    db_dir = tmp_path / "db_storage"
    msg_dir = db_dir / "message"
    msg_dir.mkdir(parents=True)
    (msg_dir / "message_0.db").write_bytes(_build_fake_db_page(key_hex))

    keys_dir = tmp_path / ".wxtools" / "keys"
    keys_dir.mkdir(parents=True)
    (tmp_path / ".wxtools" / "cache").mkdir(parents=True)
    (tmp_path / ".wxtools" / "logs").mkdir(parents=True)

    key_data = json.dumps({"message/message_0.db": key_hex})
    return db_dir, keys_dir, key_data


class TestKeyVerify:
    def test_verify_success(self, tmp_path):
        key_hex = "cc" * 32
        db_dir, keys_dir, key_data = _setup_fake_account(tmp_path, key_hex)

        # Store key in keystore (password mode for cross-platform)
        from wxtools.core.keystore import Keystore
        ks = Keystore(keys_dir)
        ks.store_key("wechat", "wxid_test", key_data.encode("ascii"),
                      protection="password", password="testpass")

        runner = CliRunner()
        with patch("wxtools.cli.commands.key.load_config") as mock_cfg, \
             patch("wxtools.cli.commands.key._resolve_account", return_value="wxid_test"):
            cfg = MagicMock()
            cfg.keys_dir = keys_dir
            cfg.get.return_value = str(db_dir)
            mock_cfg.return_value = cfg

            result = runner.invoke(cli, ["key", "verify", "--account", "wxid_test"],
                                   input="testpass\n")
            assert result.exit_code == 0
            assert "密钥验证成功" in result.output

    def test_verify_no_account(self, tmp_path):
        keys_dir = tmp_path / ".wxtools" / "keys"
        keys_dir.mkdir(parents=True)
        (tmp_path / ".wxtools" / "cache").mkdir(parents=True)
        (tmp_path / ".wxtools" / "logs").mkdir(parents=True)

        runner = CliRunner()
        with patch("wxtools.cli.commands.key.load_config") as mock_cfg, \
             patch("wxtools.cli.commands.key._resolve_account", return_value=None):
            cfg = MagicMock()
            cfg.keys_dir = keys_dir
            mock_cfg.return_value = cfg

            result = runner.invoke(cli, ["key", "verify"])
            assert result.exit_code != 0


class TestKeySet:
    def test_set_with_valid_hex_key(self, tmp_path):
        key_hex = "cc" * 32
        db_dir, keys_dir, _ = _setup_fake_account(tmp_path, key_hex)

        runner = CliRunner()
        with patch("wxtools.cli.commands.key.load_config") as mock_cfg, \
             patch("wxtools.cli.commands.key._resolve_account", return_value="wxid_test"):
            cfg = MagicMock()
            cfg.keys_dir = keys_dir

            def _cfg_get(key, default=None):
                if key == "keystore_protection":
                    return "auto"
                return str(db_dir)
            cfg.get.side_effect = _cfg_get
            mock_cfg.return_value = cfg

            # On Windows: "是否使用密码保护密钥?" → n
            # On macOS/Linux: system keychain unavailable → prompts password (twice)
            import sys
            if sys.platform == "win32":
                test_input = "n\n"
            else:
                test_input = "testpass\ntestpass\n"

            result = runner.invoke(
                cli,
                ["key", "set", "--account", "wxid_test", key_hex],
                input=test_input,
            )
            assert result.exit_code == 0
            assert "密钥已保存" in result.output

    def test_set_invalid_hex_rejected(self, tmp_path):
        keys_dir = tmp_path / ".wxtools" / "keys"
        keys_dir.mkdir(parents=True)
        (tmp_path / ".wxtools" / "cache").mkdir(parents=True)
        (tmp_path / ".wxtools" / "logs").mkdir(parents=True)

        runner = CliRunner()
        with patch("wxtools.cli.commands.key.load_config") as mock_cfg, \
             patch("wxtools.cli.commands.key._resolve_account", return_value="wxid_test"):
            cfg = MagicMock()
            cfg.keys_dir = keys_dir
            mock_cfg.return_value = cfg

            result = runner.invoke(cli, ["key", "set", "--account", "wxid_test", "not_hex"])
            assert result.exit_code != 0


class TestKeyExtractPlatformGuard:
    def test_extract_non_windows_shows_platform_error(self, tmp_path):
        keys_dir = tmp_path / ".wxtools" / "keys"
        keys_dir.mkdir(parents=True)
        (tmp_path / ".wxtools" / "cache").mkdir(parents=True)
        (tmp_path / ".wxtools" / "logs").mkdir(parents=True)

        runner = CliRunner()
        with patch("wxtools.cli.commands.key.load_config") as mock_cfg, \
             patch("wxtools.cli.commands.key._resolve_account", return_value="wxid_test"), \
             patch("wxtools.cli.commands.key.sys") as mock_sys:
            mock_sys.platform = "linux"
            cfg = MagicMock()
            cfg.keys_dir = keys_dir
            mock_cfg.return_value = cfg

            result = runner.invoke(cli, ["key", "extract"])
            assert result.exit_code != 0
            assert "key set" in result.output or "key import" in result.output
