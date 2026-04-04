from wxtools.cli.output import success_envelope, error_envelope


def test_success_envelope():
    result = success_envelope({"count": 5}, command="query")
    assert result["ok"] is True
    assert result["data"]["count"] == 5
    assert result["meta"]["command"] == "query"
    assert result["meta"]["version"] == "0.1.0"


def test_error_envelope():
    result = error_envelope("KEY_NOT_FOUND", "No key", "Extract key", command="key extract")
    assert result["ok"] is False
    assert result["error"]["code"] == "KEY_NOT_FOUND"
    assert result["error"]["remediation"] == "Extract key"
    assert result["meta"]["command"] == "key extract"
