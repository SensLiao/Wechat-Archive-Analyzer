import pytest
from unittest.mock import patch, MagicMock

from wxtools.infrastructure.wechat.key_extractor import (
    find_wechat_pid,
)


@patch("wxtools.infrastructure.wechat.key_extractor.psutil")
def test_find_wechat_pid(mock_psutil):
    proc = MagicMock()
    proc.info = {"pid": 1234, "name": "Weixin.exe"}
    proc.memory_info.return_value = MagicMock(rss=500_000_000)
    mock_psutil.process_iter.return_value = [proc]
    pid = find_wechat_pid()
    assert pid == 1234


@patch("wxtools.infrastructure.wechat.key_extractor.psutil")
def test_find_wechat_pid_not_running(mock_psutil):
    mock_psutil.process_iter.return_value = []
    from wxtools.domain.errors import WeChatNotRunningError
    with pytest.raises(WeChatNotRunningError):
        find_wechat_pid()
