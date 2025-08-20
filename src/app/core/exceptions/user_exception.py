from .general_exception import GeneralException


class UserAccountError(GeneralException):
    """
    Exception raised for errors related to user account status.

    This exception is raised when a user account is disabled and
    the user needs to contact support.

    Attributes:
        message (str): Explanation of the error. Defaults to "User account is disabled,
        please contact support".
        error_code (str): Specific error code for this type of error.
        Defaults to "USER_ACCOUNT_DISABLE".
        status_code (int): HTTP status code for the error. Defaults to 403.
    """

    def __init__(
        self,
        message="User account is disabled, please contact support",
        error_code="USER_ACCOUNT_DISABLE",
    ):
        self.message = message
        self.status_code = 403
        self.error_code = error_code
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
        )


class UserPermissionError(GeneralException):
    """
    Exception raised for user permission errors.

    Attributes:
        message (str): Explanation of the error.
        status_code (int): HTTP status code for the error.
        error_code (str): Specific error code for the permission error.

    Args:
        message (str, optional): Custom error message.
        Defaults to "user don't have sufficient permission".
    """

    def __init__(self, message="user don't have sufficient permission"):
        self.message = message
        self.status_code = 403
        self.error_code = "PERMISSION_ERROR"
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
        )
