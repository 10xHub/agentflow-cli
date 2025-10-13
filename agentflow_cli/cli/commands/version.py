"""Version command implementation."""

import tomllib
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import CLI_VERSION, PROJECT_ROOT


class VersionCommand(BaseCommand):
    """Command to display version information."""

    def execute(self, **kwargs: Any) -> int:
        """Execute the version command.

        Returns:
            Exit code
        """
        try:
            # Print banner
            self.output.print_banner(
                "Version",
                "Show pyagenity CLI and package version info",
                color="green",
            )

            # Get package version from pyproject.toml
            pkg_version = self._read_package_version()

            self.output.success(f"agentflow-cli CLI\n  Version: {CLI_VERSION}")
            self.output.info(f"agentflow-cli Package\n  Version: {pkg_version}")

            return 0

        except Exception as e:
            return self.handle_error(e)

    def _read_package_version(self) -> str:
        """Read package version from pyproject.toml.

        Returns:
            Package version string
        """
        try:
            pyproject_path = PROJECT_ROOT / "pyproject.toml"
            with pyproject_path.open("rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("version", "unknown")
        except Exception:
            return "unknown"
