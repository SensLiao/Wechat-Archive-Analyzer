from pathlib import Path
from wxtools.plugins.wechat.account_discovery import discover_accounts, find_wechat_data_dir


def test_discover_accounts_from_fake_dir(tmp_path):
    wxid_dir = tmp_path / "xwechat_files" / "wxid_abc123"
    db_dir = wxid_dir / "db_storage"
    db_dir.mkdir(parents=True)
    (db_dir / "MicroMsg.db").write_bytes(b"fake")

    accounts = discover_accounts(str(tmp_path / "xwechat_files"))
    assert len(accounts) == 1
    assert accounts[0]["wxid"] == "wxid_abc123"


def test_discover_accounts_empty_dir(tmp_path):
    accounts = discover_accounts(str(tmp_path))
    assert accounts == []


def test_find_wechat_data_dir_4x(tmp_path):
    docs = tmp_path / "Documents"
    xdir = docs / "xwechat_files"
    xdir.mkdir(parents=True)
    result = find_wechat_data_dir(documents_dir=docs)
    assert result == xdir


def test_find_wechat_data_dir_3x_fallback(tmp_path):
    docs = tmp_path / "Documents"
    wdir = docs / "WeChat Files"
    wdir.mkdir(parents=True)
    result = find_wechat_data_dir(documents_dir=docs)
    assert result == wdir


def test_find_wechat_data_dir_none(tmp_path):
    docs = tmp_path / "Documents"
    docs.mkdir(parents=True)
    result = find_wechat_data_dir(documents_dir=docs)
    assert result is None
