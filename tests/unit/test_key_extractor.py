import sys
import pytest
from unittest.mock import patch, MagicMock

from wxtools.plugins.wechat.key_extractor import (
    find_wechat_pid,
    is_valid_hex_key,
    extract_key_candidates_from_buffer,
)


def test_is_valid_hex_key():
    assert is_valid_hex_key("ab" * 32) is True
    assert is_valid_hex_key("AB" * 32) is True
    assert is_valid_hex_key("ab" * 31) is False
    assert is_valid_hex_key("zz" * 32) is False
    assert is_valid_hex_key("") is False


def test_extract_key_candidates_from_buffer():
    fake_key = "ab" * 32
    buffer = b"random_prefix_" + fake_key.encode("ascii") + b"_random_suffix"
    candidates = extract_key_candidates_from_buffer(buffer)
    assert fake_key in candidates


def test_extract_key_candidates_no_match():
    buffer = b"this has no hex keys in it at all just random text"
    candidates = extract_key_candidates_from_buffer(buffer)
    assert len(candidates) == 0


@patch("wxtools.plugins.wechat.key_extractor.psutil")
def test_find_wechat_pid(mock_psutil):
    proc = MagicMock()
    proc.info = {"pid": 1234, "name": "Weixin.exe"}
    proc.memory_info.return_value = MagicMock(rss=500_000_000)
    mock_psutil.process_iter.return_value = [proc]
    pid = find_wechat_pid()
    assert pid == 1234


@patch("wxtools.plugins.wechat.key_extractor.psutil")
def test_find_wechat_pid_not_running(mock_psutil):
    mock_psutil.process_iter.return_value = []
    from wxtools.core.errors import WeChatNotRunningError
    with pytest.raises(WeChatNotRunningError):
        find_wechat_pid()
