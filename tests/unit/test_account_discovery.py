from pathlib import Path
from wxtools.plugins.wechat.account_discovery import discover_accounts, find_wechat_data_dir


def test_discover_accounts_from_fake_dir(tmp_path):
    wxid_dir = tmp_path / "xwechat_files" / "wxid_abc123"
    db_dir = wxid_dir / "db_storage"
    db_dir.mkdir(parents=True)
    (db_dir / "contact.db").write_bytes(b"fake")

    accounts = discover_accounts(str(tmp_path / "xwechat_files"))
    assert len(accounts) == 1
    assert accounts[0]["wxid"] == "wxid_abc123"
    assert accounts[0]["version"] == "4.x"


def test_discover_accounts_4x_with_suffix(tmp_path):
    wxid_dir = tmp_path / "xwechat_files" / "wxid_abc123_0739"
    db_dir = wxid_dir / "db_storage"
    db_dir.mkdir(parents=True)

    accounts = discover_accounts(str(tmp_path / "xwechat_files"))
    assert len(accounts) == 1
    assert accounts[0]["wxid"] == "wxid_abc123"


def test_discover_accounts_empty_dir(tmp_path):
    accounts = discover_accounts(str(tmp_path))
    assert accounts == []


def test_find_wechat_data_dir_4x(tmp_path):
    # WeChat 4.x stores directly under user home
    xdir = tmp_path / "xwechat_files"
    xdir.mkdir(parents=True)
    result = find_wechat_data_dir(home_dir=tmp_path)
    assert result == xdir


def test_find_wechat_data_dir_4x_documents(tmp_path):
    # Some installations put it under Documents
    xdir = tmp_path / "Documents" / "xwechat_files"
    xdir.mkdir(parents=True)
    result = find_wechat_data_dir(home_dir=tmp_path)
    assert result == xdir


def test_find_wechat_data_dir_3x_fallback(tmp_path):
    wdir = tmp_path / "Documents" / "WeChat Files"
    wdir.mkdir(parents=True)
    result = find_wechat_data_dir(home_dir=tmp_path)
    assert result == wdir


def test_find_wechat_data_dir_none(tmp_path):
    result = find_wechat_data_dir(home_dir=tmp_path)
    assert result is None
