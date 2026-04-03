"""SQLCipher decryption via CLI subprocess."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from wxtools.core.errors import DbDecryptFailedError, DbNotFoundError

logger = logging.getLogger("wxtools.decryptor")

PRAGMA_COMMANDS = """PRAGMA key = "x'{key}'";
PRAGMA cipher_page_size = 4096;
PRAGMA kdf_iter = 256000;
PRAGMA cipher_hmac_algorithm = HMAC_SHA256;
PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512;
ATTACH DATABASE '{output}' AS plaintext KEY '';
SELECT sqlcipher_export('plaintext');
DETACH DATABASE plaintext;
"""


def _needs_redecrypt(source: Path, cache: Path) -> bool:
    if not cache.exists():
        return True
    return source.stat().st_mtime > cache.stat().st_mtime


class Decryptor:
    def __init__(self, sqlcipher_path: str = "sqlcipher"):
        self._sqlcipher_path = sqlcipher_path

    def decrypt_all(
        self,
        source_dir: Path,
        cache_dir: Path,
        key_hex: str,
        db_patterns: Optional[List[str]] = None,
    ) -> List[Path]:
        if db_patterns is None:
            db_patterns = ["MicroMsg.db", "MSG*.db", "ChatRoomUser.db"]

        cache_dir.mkdir(parents=True, exist_ok=True)
        decrypted: List[Path] = []

        for pattern in db_patterns:
            for source_db in sorted(source_dir.glob(pattern)):
                cache_db = cache_dir / source_db.name
                if _needs_redecrypt(source_db, cache_db):
                    logger.info("Decrypting %s", source_db.name)
                    self._snapshot_and_decrypt(source_db, cache_db, key_hex)
                else:
                    logger.info("Cache up-to-date: %s", source_db.name)
                decrypted.append(cache_db)

        return decrypted

    def _snapshot_and_decrypt(self, source: Path, dest: Path, key_hex: str) -> None:
        with tempfile.TemporaryDirectory(prefix="wxtools_") as tmpdir:
            tmp_source = Path(tmpdir) / source.name
            shutil.copy2(source, tmp_source)
            for suffix in ["-wal", "-shm"]:
                wal = source.with_name(source.name + suffix)
                if wal.exists():
                    shutil.copy2(wal, Path(tmpdir) / wal.name)

            tmp_dest = Path(tmpdir) / f"{source.stem}_plain.db"
            self._run_sqlcipher_decrypt(tmp_source, tmp_dest, key_hex)

            dest_tmp = dest.with_suffix(".tmp")
            shutil.move(str(tmp_dest), str(dest_tmp))
            os.replace(str(dest_tmp), str(dest))

    def _run_sqlcipher_decrypt(self, source: Path, dest: Path, key_hex: str) -> None:
        commands = PRAGMA_COMMANDS.format(
            key=key_hex,
            output=str(dest).replace("\\", "/"),
        )
        try:
            result = subprocess.run(
                [self._sqlcipher_path, str(source)],
                input=commands,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.error("sqlcipher failed: %s", result.stderr)
                raise DbDecryptFailedError()
        except FileNotFoundError:
            raise DbDecryptFailedError()
        except subprocess.TimeoutExpired:
            raise DbDecryptFailedError()
