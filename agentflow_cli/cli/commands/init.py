"""Init command implementation."""

from pathlib import Path
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.exceptions import FileOperationError
from agentflow_cli.cli.templates.defaults import (
    DEFAULT_CONFIG_JSON,
    DEFAULT_PRE_COMMIT,
    DEFAULT_PYPROJECT,
    DEFAULT_REACT_PY,
)


class InitCommand(BaseCommand):
    """Command to initialize default config and graph files."""

    def execute(
        self,
        path: str = ".",
        force: bool = False,
        prod: bool = False,
        **kwargs: Any,
    ) -> int:
        """Execute the init command.

        Args:
            path: Directory to initialize files in
            force: Overwrite existing files
            prod: Include production config files
            **kwargs: Additional arguments

        Returns:
            Exit code
        """
        try:
            # Print banner
            subtitle = "Create agentflow.json and graph/react.py scaffold files"
            if prod:
                subtitle += " plus production config files"
            self.output.print_banner("Init", subtitle, color="magenta")

            base_path = Path(path)

            # Create directory if it doesn't exist
            base_path.mkdir(parents=True, exist_ok=True)

            # Write config JSON
            config_path = base_path / "agentflow.json"
            self._write_file(config_path, DEFAULT_CONFIG_JSON + "\n", force=force)

            # Write graph/react.py
            graph_dir = base_path / "graph"
            graph_dir.mkdir(parents=True, exist_ok=True)

            react_path = graph_dir / "react.py"
            self._write_file(react_path, DEFAULT_REACT_PY, force=force)

            # Write __init__.py to make graph a package
            init_path = graph_dir / "__init__.py"
            self._write_file(init_path, "", force=force)

            # Production extra files
            if prod:
                pre_commit_path = base_path / ".pre-commit-config.yaml"
                pyproject_path = base_path / "pyproject.toml"
                self._write_file(pre_commit_path, DEFAULT_PRE_COMMIT + "\n", force=force)
                self._write_file(pyproject_path, DEFAULT_PYPROJECT + "\n", force=force)
                self.output.success(f"Created pre-commit config at {pre_commit_path}")
                self.output.success(f"Created pyproject file at {pyproject_path}")

            # Success messages
            self.output.success(f"Created config file at {config_path}")
            self.output.success(f"Created react graph at {react_path}")
            self.output.success(f"Created graph package at {init_path}")

            # Next steps
            self.output.info("\n🚀 Next steps:")
            next_steps = [
                "Review and customize agentflow.json configuration",
                "Modify graph/react.py to implement your agent logic",
                "Set up environment variables in .env file",
                "Run the API server with: pag api",
            ]
            if prod:
                next_steps.insert(0, "Install pre-commit hooks: pre-commit install")
                next_steps.insert(1, "Review pyproject.toml for metadata updates")

            for i, step in enumerate(next_steps, 1):
                self.output.info(f"{i}. {step}")

            return 0

        except FileOperationError as e:
            return self.handle_error(e)
        except Exception as e:
            file_error = FileOperationError(f"Failed to initialize project: {e}")
            return self.handle_error(file_error)

    def _write_file(self, path: Path, content: str, *, force: bool) -> None:
        """Write content to path, creating parents.

        Args:
            path: Path to write to
            content: Content to write
            force: Whether to overwrite existing files

        Raises:
            FileOperationError: If file exists and force is False, or write fails
        """
        try:
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file exists and force is not set
            if path.exists() and not force:
                raise FileOperationError(
                    f"File already exists: {path}. Use --force to overwrite.", file_path=str(path)
                )

            # Write the file
            path.write_text(content, encoding="utf-8")
            self.logger.debug(f"Successfully wrote file: {path}")

        except OSError as e:
            raise FileOperationError(
                f"Failed to write file {path}: {e}", file_path=str(path)
            ) from e
