from agentflow_cli.src.app.core.exceptions.general_exception import GeneralException
from agentflow_cli.src.app.core.exceptions.user_exception import (
    UserAccountError,
    UserPermissionError,
)


HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403


def test_general_exception_str_and_fields():
    exc = GeneralException(message="boom", status_code=HTTP_BAD_REQUEST, error_code="APP_ERR")
    s = str(exc)
    assert "boom" in s and "APP_ERR" in s and str(HTTP_BAD_REQUEST) in s


def test_user_account_error_defaults():
    exc = UserAccountError()
    assert exc.status_code == HTTP_FORBIDDEN
    assert exc.error_code == "USER_ACCOUNT_DISABLE"
    assert "disabled" in exc.message


def test_user_permission_error_defaults():
    exc = UserPermissionError()
    assert exc.status_code == HTTP_FORBIDDEN
    assert exc.error_code == "PERMISSION_ERROR"
    assert "permission" in exc.message
