"""Version command implementation."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import CLI_VERSION


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
                "Show Agentflow CLI and package version info",
                color="green",
            )

            core_version = self._core_version()

            self.output.success(f"10xscale-agentflow-cli\n  Version: {CLI_VERSION}")
            self.output.info(f"10xscale-agentflow (core)\n  Version: {core_version}")

            return 0

        except Exception as e:
            return self.handle_error(e)

    @staticmethod
    def _core_version() -> str:
        """Resolve the installed core framework version.

        Returns:
            Version string, or ``"not installed"`` when the core package is absent.
        """
        try:
            return _pkg_version("10xscale-agentflow")
        except PackageNotFoundError:
            return "not installed"
