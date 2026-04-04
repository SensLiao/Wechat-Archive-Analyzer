"""Tests for cross-platform ACL helpers."""
import os
import stat
import sys
import pytest
from wxtools.core.acl import secure_dir

def test_secure_dir_creates_directory(tmp_path):
    target = tmp_path / "secret"
    secure_dir(target)
    assert target.is_dir()

def test_secure_dir_idempotent(tmp_path):
    target = tmp_path / "secret"
    secure_dir(target)
    secure_dir(target)
    assert target.is_dir()

@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission check")
def test_secure_dir_sets_0700_on_posix(tmp_path):
    target = tmp_path / "secret"
    secure_dir(target)
    mode = stat.S_IMODE(os.stat(target).st_mode)
    assert mode == 0o700
