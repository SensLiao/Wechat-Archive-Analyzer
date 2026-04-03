from wxtools.core.errors import WxToolsError, KeyNotFoundError, AdminRequiredError


def test_wxtools_error_has_code_message_remediation():
    err = WxToolsError("TEST_CODE", "test message", "do something")
    assert err.code == "TEST_CODE"
    assert err.message == "test message"
    assert err.remediation == "do something"
    assert str(err) == "test message"


def test_key_not_found_error():
    err = KeyNotFoundError()
    assert err.code == "KEY_NOT_FOUND"
    assert "extract" in err.remediation.lower()


def test_admin_required_error():
    err = AdminRequiredError()
    assert err.code == "ADMIN_REQUIRED"


def test_error_to_dict():
    err = WxToolsError("CODE", "msg", "fix it")
    d = err.to_dict()
    assert d == {"code": "CODE", "message": "msg", "remediation": "fix it"}
