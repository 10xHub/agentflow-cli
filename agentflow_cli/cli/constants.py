"""CLI constants and configuration values."""

from pathlib import Path
from typing import Final


# Version information
CLI_VERSION: Final[str] = "1.0.0"

# Default configuration values
DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8000
DEFAULT_CONFIG_FILE: Final[str] = "agentflow.json"
DEFAULT_PYTHON_VERSION: Final[str] = "3.13"
DEFAULT_SERVICE_NAME: Final[str] = "agentflow-api"

# File paths and names
CONFIG_FILENAMES: Final[list[str]] = [
    "agentflow.json",
    ".agentflow.json",
    "agentflow.config.json",
]

REQUIREMENTS_PATHS: Final[list[str]] = [
    "requirements.txt",
    "requirements/requirements.txt",
    "requirements/base.txt",
    "requirements/production.txt",
]

# Docker and container configuration
DOCKERFILE_NAME: Final[str] = "Dockerfile"
DOCKER_COMPOSE_NAME: Final[str] = "docker-compose.yml"
HEALTH_CHECK_ENDPOINT: Final[str] = "/ping"

# Logging configuration
LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# Environment variables
ENV_GRAPH_PATH: Final[str] = "GRAPH_PATH"
ENV_PYTHONPATH: Final[str] = "PYTHONPATH"
ENV_PYTHONDONTWRITEBYTECODE: Final[str] = "PYTHONDONTWRITEBYTECODE"
ENV_PYTHONUNBUFFERED: Final[str] = "PYTHONUNBUFFERED"

# Exit codes
EXIT_SUCCESS: Final[int] = 0
EXIT_FAILURE: Final[int] = 1
EXIT_CONFIG_ERROR: Final[int] = 2
EXIT_VALIDATION_ERROR: Final[int] = 3


# Output styling
class Colors:
    """ANSI color codes for terminal output."""

    RESET: Final[str] = "\033[0m"
    RED: Final[str] = "\033[91m"
    GREEN: Final[str] = "\033[92m"
    YELLOW: Final[str] = "\033[93m"
    BLUE: Final[str] = "\033[94m"
    MAGENTA: Final[str] = "\033[95m"
    CYAN: Final[str] = "\033[96m"
    WHITE: Final[str] = "\033[97m"

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Apply color to text."""
        color_code = getattr(cls, color.upper(), cls.RESET)
        return f"{color_code}{text}{cls.RESET}"


# Emoji and symbols for output
EMOJI_SUCCESS: Final[str] = "✅"
EMOJI_ERROR: Final[str] = "⚠️"
EMOJI_INFO: Final[str] = "📋"
EMOJI_SPARKLE: Final[str] = "✨"
EMOJI_ROCKET: Final[str] = "🚀"
EMOJI_PACKAGE: Final[str] = "📦"

# Project structure
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
CLI_ROOT: Final[Path] = Path(__file__).parent
TEMPLATES_DIR: Final[Path] = CLI_ROOT / "templates"
