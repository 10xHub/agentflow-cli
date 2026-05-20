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

            if type(self.output).__name__ == "OutputFormatter":
                from rich.panel import Panel
                from rich.table import Table
                from rich import box
                import platform
                import sys

                # Build a beautifully styled table
                table = Table(box=box.ROUNDED, border_style="cyan", show_header=True, expand=False)
                table.add_column("Component", style="bold magenta", justify="left")
                table.add_column("Version Details", style="white", justify="left")

                table.add_row("CLI CLI Version", f"[bold green]{CLI_VERSION}[/bold green]")
                table.add_row("Package Version", f"[bold cyan]{pkg_version}[/bold cyan]")
                table.add_row("Python Version", f"[dim white]{sys.version.split()[0]}[/dim white]")
                table.add_row("OS Platform", f"[dim white]{platform.system()} {platform.release()}[/dim white]")

                panel = Panel(
                    table,
                    title="[bold green]System & Package Information[/bold green]",
                    border_style="green",
                    expand=False,
                    padding=(1, 2)
                )
                self.output.console.print(panel)
                self.output.console.print("")
            else:
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
