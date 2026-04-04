import sys
import pytest
from unittest.mock import patch, MagicMock

from wxtools.plugins.wechat.key_extractor import (
    find_wechat_pid,
)


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
