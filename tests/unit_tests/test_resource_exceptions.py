from agentflow_cli.src.app.core.exceptions.resources_exceptions import (
    InvalidOperationError,
    ResourceDuplicationError,
    ResourceNotFoundError,
)


HTTP_NOT_FOUND = 404
HTTP_FORBIDDEN = 403


def test_resource_not_found_defaults():
    exc = ResourceNotFoundError()
    assert exc.status_code == HTTP_NOT_FOUND
    assert exc.error_code == "RESOURCE_NOT_FOUND"
    assert "not found" in exc.message.lower()


def test_resource_duplication_defaults():
    exc = ResourceDuplicationError()
    assert exc.status_code == HTTP_FORBIDDEN
    assert exc.error_code == "DUPLICATE_REQUEST"
    assert "duplicate" in exc.message.lower()


def test_invalid_operation_defaults():
    exc = InvalidOperationError()
    assert exc.status_code == HTTP_FORBIDDEN
    assert exc.error_code == "InvalidOperationError"
    assert "operation" in exc.message.lower()
