"""Tests for attachment path resolution, existence check, and copy."""
import shutil
from pathlib import Path
import pytest
from wxtools.plugins.wechat.attachment_resolver import AttachmentResolver


@pytest.fixture
def resolver(tmp_path):
    data_root = tmp_path / "wechat_data"
    data_root.mkdir()
    return AttachmentResolver(data_root)


def test_resolve_image_path(resolver, tmp_path):
    img_dir = tmp_path / "wechat_data" / "FileStorage" / "Image" / "2026-01"
    img_dir.mkdir(parents=True)
    (img_dir / "abc123.jpg").write_bytes(b"\xff\xd8\xff")
    content_xml = '<msg><img cdnthumburl="" aeskey="abc123" /></msg>'
    path = resolver.resolve_path("image", content_xml)
    assert path is not None
    assert "Image" in path


def test_resolve_returns_none_for_text(resolver):
    path = resolver.resolve_path("text", "hello world")
    assert path is None


def test_check_exists_true(resolver, tmp_path):
    f = tmp_path / "wechat_data" / "FileStorage" / "test.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("test")
    assert resolver.check_exists(str(f)) is True


def test_check_exists_false(resolver):
    assert resolver.check_exists("/nonexistent/file.txt") is False


def test_path_traversal_blocked(resolver, tmp_path):
    evil_path = str(tmp_path / "wechat_data" / ".." / ".." / "etc" / "passwd")
    assert resolver.check_exists(evil_path) is False


def test_copy_to_export(resolver, tmp_path):
    src = tmp_path / "wechat_data" / "FileStorage" / "File" / "doc.pdf"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"%PDF-1.4")
    export_dir = tmp_path / "export"
    rel = resolver.copy_to_export(str(src), export_dir)
    assert rel is not None
    assert (export_dir / "attachments" / rel).exists()


def test_copy_traversal_blocked(resolver, tmp_path):
    evil = tmp_path / "outside" / "secret.txt"
    evil.parent.mkdir(parents=True, exist_ok=True)
    evil.write_text("secret")
    export_dir = tmp_path / "export"
    rel = resolver.copy_to_export(str(evil), export_dir)
    assert rel is None
