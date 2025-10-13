from agentflow_cli.src.app.utils.schemas import ErrorSchemas


class GeneralException(Exception):
    """
    A custom exception class to handle general application errors.

    Attributes:
        message (str): Description of the error.
        status_code (int): HTTP status code associated with the error.
        error_code (str): Application-specific error code.
        details (list[ErrorSchemas]): Optional list of detailed error schemas.

    Methods:
        __str__(): Returns a string representation of the exception.
    """

    def __init__(
        self,
        message="An error occurred",
        status_code=400,
        error_code="APP_ERROR",
        details: list[ErrorSchemas] | None = None,
    ):
        """
        Initializes a GeneralException instance.

        Args:
            message (str, optional):
                Description of the error. Defaults to "An error occurred".
            status_code (int, optional):
                HTTP status code associated with the error. Defaults to 400.
            error_code (str, optional):
                Application-specific error code. Defaults to "APP_ERROR".
            details (list[ErrorSchemas], optional):
                Optional list of detailed error schemas.
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        """
        Returns the string representation of the GeneralException instance.

        Returns:
            str: A string containing the message, status code, and error code.
        """
        return (
            "message: "
            + self.message
            + " status_code: "
            + str(self.status_code)
            + " error_code: "
            + self.error_code
        )
