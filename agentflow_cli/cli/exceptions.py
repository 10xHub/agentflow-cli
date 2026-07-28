"""Custom exceptions for the Agentflow CLI."""

from __future__ import annotations

from collections.abc import Sequence


class AgentflowCLIError(Exception):
    """Base exception for all Agentflow CLI errors."""

    def __init__(
        self,
        message: str,
        exit_code: int = 1,
        *,
        code: str = "AF-CMD-001",
        hints: Sequence[str] = (),
        docs_url: str | None = None,
    ) -> None:
        """Initialize the exception with a message and exit code.

        Args:
            message: Error message to display
            exit_code: Exit code to use when terminating
        """
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.code = code
        self.hints = tuple(hints)
        self.docs_url = docs_url


class ConfigurationError(AgentflowCLIError):
    """Raised when there are configuration-related errors."""

    def __init__(self, message: str, config_path: str | None = None) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            config_path: Path to the problematic config file
        """
        super().__init__(message, exit_code=2, code="AF-CONFIG-001")
        self.config_path = config_path


class ValidationError(AgentflowCLIError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field: Name of the field that failed validation
        """
        super().__init__(message, exit_code=3, code="AF-INPUT-001")
        self.field = field


class FileOperationError(AgentflowCLIError):
    """Raised when file operations fail."""

    def __init__(self, message: str, file_path: str | None = None) -> None:
        """Initialize file operation error.

        Args:
            message: Error message
            file_path: Path to the problematic file
        """
        super().__init__(message, exit_code=1, code="AF-FILE-001")
        self.file_path = file_path


class TemplateError(AgentflowCLIError):
    """Raised when template operations fail."""

    def __init__(self, message: str, template_name: str | None = None) -> None:
        """Initialize template error.

        Args:
            message: Error message
            template_name: Name of the problematic template
        """
        super().__init__(message, exit_code=1, code="AF-TEMPLATE-001")
        self.template_name = template_name


class ServerError(AgentflowCLIError):
    """Raised when server operations fail."""

    def __init__(self, message: str, host: str | None = None, port: int | None = None) -> None:
        """Initialize server error.

        Args:
            message: Error message
            host: Server host
            port: Server port
        """
        super().__init__(message, exit_code=1, code="AF-SERVER-001")
        self.host = host
        self.port = port


class DockerError(AgentflowCLIError):
    """Raised when Docker-related operations fail."""

    def __init__(self, message: str, dockerfile_path: str | None = None) -> None:
        """Initialize Docker error.

        Args:
            message: Error message
            dockerfile_path: Path to the Dockerfile
        """
        super().__init__(message, exit_code=1, code="AF-DOCKER-001")
        self.dockerfile_path = dockerfile_path


class DependencyError(AgentflowCLIError):
    """Raised when an optional feature dependency is missing or incompatible."""

    def __init__(self, message: str, *, hints: Sequence[str] = ()) -> None:
        super().__init__(
            message,
            exit_code=4,
            code="AF-DEPS-001",
            hints=hints,
        )
