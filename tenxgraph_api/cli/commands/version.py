"""Version command implementation."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from typing import Any

from tenxgraph_api.cli.commands import BaseCommand
from tenxgraph_api.cli.constants import CLI_VERSION


class VersionCommand(BaseCommand):
    """Command to display version information."""

    def execute(self, **kwargs: Any) -> int:
        """Execute the version command.

        Returns:
            Exit code
        """
        try:
            self.output.command_header(
                "version",
                "Show 10xGraph CLI and package version info",
                color="green",
            )

            core_version = self._core_version()

            self.output.success(f"10xgraph-api\n  Version: {CLI_VERSION}")
            self.output.info(f"10xgraph (core)\n  Version: {core_version}")

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
            return _pkg_version("10xgraph")
        except PackageNotFoundError:
            return "not installed"
