from .general_exception import GeneralException


class ResourceNotFoundError(GeneralException):
    """
    Exception raised when a requested resource is not found.

    Attributes:
        message (str): Explanation of the error.
        status_code (int): HTTP status code for the error.
        error_code (str): Specific error code for the error.
    """

    # Implementation here
    def __init__(self, message="Resources not found"):
        self.message = message
        self.status_code = 404
        self.error_code = "RESOURCE_NOT_FOUND"
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
        )


class ResourceDuplicationError(GeneralException):
    """
    Exception raised for duplicate resource requests.

    This exception is used to indicate that a request has been made for a resource
    that already exists, and such duplication is not allowed.

    Attributes:
        message (str): Explanation of the error. Defaults to "Duplicate request".
        status_code (int): HTTP status code for the error. Defaults to 403.
        error_code (str): Specific error code for duplicate requests.
        Defaults to "DUPLICATE_REQUEST".
    """

    def __init__(self, message="Duplicate request"):
        self.message = message
        self.status_code = 403
        self.error_code = "DUPLICATE_REQUEST"
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
        )


class InvalidOperationError(GeneralException):
    """
    Exception raised for invalid operations.

    This exception is used to indicate that a particular operation is not supported.

    Attributes:
        message (str): Explanation of the error. Defaults to "Operation Not Supported".
        status_code (int): HTTP status code for the error. Defaults to 403.
        error_code (str): Specific error code for the exception.
        Defaults to "InvalidOperationError".
    """

    def __init__(self, message="Operation Not Supported"):
        self.message = message
        self.status_code = 403
        self.error_code = "InvalidOperationError"
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
        )
