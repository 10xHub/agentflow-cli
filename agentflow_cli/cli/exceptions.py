"""Custom exceptions for the Pyagenity CLI."""


class PyagenityCLIError(Exception):
    """Base exception for all Pyagenity CLI errors."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        """Initialize the exception with a message and exit code.

        Args:
            message: Error message to display
            exit_code: Exit code to use when terminating
        """
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


class ConfigurationError(PyagenityCLIError):
    """Raised when there are configuration-related errors."""

    def __init__(self, message: str, config_path: str | None = None) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            config_path: Path to the problematic config file
        """
        super().__init__(message, exit_code=2)
        self.config_path = config_path


class ValidationError(PyagenityCLIError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field: Name of the field that failed validation
        """
        super().__init__(message, exit_code=3)
        self.field = field


class FileOperationError(PyagenityCLIError):
    """Raised when file operations fail."""

    def __init__(self, message: str, file_path: str | None = None) -> None:
        """Initialize file operation error.

        Args:
            message: Error message
            file_path: Path to the problematic file
        """
        super().__init__(message, exit_code=1)
        self.file_path = file_path


class TemplateError(PyagenityCLIError):
    """Raised when template operations fail."""

    def __init__(self, message: str, template_name: str | None = None) -> None:
        """Initialize template error.

        Args:
            message: Error message
            template_name: Name of the problematic template
        """
        super().__init__(message, exit_code=1)
        self.template_name = template_name


class ServerError(PyagenityCLIError):
    """Raised when server operations fail."""

    def __init__(self, message: str, host: str | None = None, port: int | None = None) -> None:
        """Initialize server error.

        Args:
            message: Error message
            host: Server host
            port: Server port
        """
        super().__init__(message, exit_code=1)
        self.host = host
        self.port = port


class DockerError(PyagenityCLIError):
    """Raised when Docker-related operations fail."""

    def __init__(self, message: str, dockerfile_path: str | None = None) -> None:
        """Initialize Docker error.

        Args:
            message: Error message
            dockerfile_path: Path to the Dockerfile
        """
        super().__init__(message, exit_code=1)
        self.dockerfile_path = dockerfile_path
