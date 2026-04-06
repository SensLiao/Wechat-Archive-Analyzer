import logging
from wxtools.runtime.logging_setup import setup_logging, RedactionFilter


def test_redaction_filter_masks_key():
    filt = RedactionFilter()
    record = logging.LogRecord(
        "test", logging.INFO, "", 0, "Key is abc12345def67890abc12345def67890abc12345def67890abc12345def67890", (), None
    )
    filt.filter(record)
    assert "abc12345" in record.msg
    assert "7890" in record.msg
    assert "def67890abc12345def67890abc12345def67890abc12345def6" not in record.msg


def test_redaction_filter_passes_normal_message():
    filt = RedactionFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "Normal log message", (), None)
    result = filt.filter(record)
    assert result is True
    assert record.msg == "Normal log message"


def test_setup_logging_returns_logger(tmp_path):
    logger = setup_logging(verbosity=0, json_mode=False, log_dir=tmp_path)
    assert isinstance(logger, logging.Logger)
