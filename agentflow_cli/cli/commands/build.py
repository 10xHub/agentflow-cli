"""Build command implementation."""

from pathlib import Path
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import DEFAULT_PORT, DEFAULT_PYTHON_VERSION, DEFAULT_SERVICE_NAME
from agentflow_cli.cli.core.validation import Validator
from agentflow_cli.cli.exceptions import DockerError, FileOperationError, ValidationError
from agentflow_cli.cli.templates.defaults import (
    generate_docker_compose_content,
    generate_dockerfile_content,
    generate_dockerignore_content,
    generate_k8s_manifest_content,
)


class BuildCommand(BaseCommand):
    """Command to generate Dockerfile and docker-compose.yml for the application."""

    def execute(
        self,
        output_file: str = "Dockerfile",
        force: bool = False,
        python_version: str = DEFAULT_PYTHON_VERSION,
        port: int = DEFAULT_PORT,
        docker_compose: bool = False,
        k8s: bool = False,
        service_name: str = DEFAULT_SERVICE_NAME,
        **kwargs: Any,
    ) -> int:
        """Execute the build command.

        Args:
            output_file: Output Dockerfile path
            force: Overwrite existing files
            python_version: Python version to use
            port: Port to expose
            docker_compose: Generate docker-compose.yml
            k8s: Generate a Kubernetes manifest (Deployment + Service)
            service_name: Service name for docker-compose
            **kwargs: Additional arguments

        Returns:
            Exit code
        """
        try:
            self.output.command_header(
                "build",
                "Generate Dockerfile (and optional docker-compose.yml) for production image",
                color="yellow",
            )

            # Validate inputs
            validated_port = Validator.validate_port(port)
            validated_python_version = Validator.validate_python_version(python_version)
            validated_service_name = Validator.validate_service_name(service_name)
            output_path = Validator.validate_path(output_file)

            current_dir = Path.cwd()

            # Check if Dockerfile already exists
            if output_path.exists() and not force:
                raise FileOperationError(
                    f"Dockerfile already exists at {output_path}. Use --force to overwrite.",
                    file_path=str(output_path),
                )

            # Discover requirements files
            requirements_files, requirements_file = self._discover_requirements(current_dir)

            with self.output.activity(
                "Generating container assets",
                done="Container assets generated",
                spinner="material",
            ):
                dockerfile_content = generate_dockerfile_content(
                    python_version=validated_python_version,
                    port=validated_port,
                    requirements_file=requirements_file,
                    has_requirements=bool(requirements_files),
                    omit_cmd=docker_compose,
                )
                self._write_dockerfile(output_path, dockerfile_content)
            self.output.success(f"Successfully generated Dockerfile at {output_path}")

            # Write .dockerignore in the same directory
            dockerignore_path = output_path.parent / ".dockerignore"
            if not dockerignore_path.exists() or force:
                try:
                    dockerignore_content = generate_dockerignore_content()
                    dockerignore_path.write_text(dockerignore_content, encoding="utf-8")
                    self.output.success(
                        f"Successfully generated .dockerignore at {dockerignore_path}"
                    )
                except Exception as e:
                    self.output.warning(f"Could not generate .dockerignore: {e}")

            # Show requirements info
            if requirements_files:
                self.output.info(f"Using requirements file: {requirements_files[0]}")
            else:
                self.output.warning(
                    "No requirements.txt found - will install agentflow-cli from PyPI"
                )

            # Generate docker-compose.yml if requested
            if docker_compose:
                self._write_docker_compose(
                    force=force, service_name=validated_service_name, port=validated_port
                )

            # Generate a Kubernetes manifest if requested
            if k8s:
                self._write_k8s_manifest(
                    force=force, service_name=validated_service_name, port=validated_port
                )

            generated = ["Dockerfile", ".dockerignore"]
            if docker_compose:
                generated.append("docker-compose.yml")
            if k8s:
                generated.append("k8s.yaml")
            self.output.completion_screen(
                "Build assets ready",
                "Deployment files generated successfully",
                details={
                    "Files": ", ".join(generated),
                    "Service": validated_service_name,
                    "Port": validated_port,
                },
                next_steps=(
                    ["docker compose up --build"]
                    if docker_compose
                    else [f"docker build -t {validated_service_name} ."]
                ),
            )

            return 0

        except (ValidationError, DockerError, FileOperationError) as e:
            return self.handle_error(e)
        except Exception as e:
            docker_error = DockerError(f"Failed to generate Docker files: {e}")
            return self.handle_error(docker_error)

    def _discover_requirements(self, current_dir: Path) -> tuple[list[Path], str]:
        """Discover requirements files in the project.

        Args:
            current_dir: Current directory to search in

        Returns:
            Tuple of (found_files_list, chosen_filename_str)
        """
        requirements_files = []
        requirements_paths = [
            current_dir / "requirements.txt",
            current_dir / "requirements" / "requirements.txt",
            current_dir / "requirements" / "base.txt",
            current_dir / "requirements" / "production.txt",
        ]

        for req_path in requirements_paths:
            if req_path.exists():
                requirements_files.append(req_path)

        if not requirements_files:
            self.logger.warning("No requirements.txt file found in common locations")

        requirements_file = "requirements.txt"
        if requirements_files:
            requirements_file = requirements_files[0].name
            if len(requirements_files) > 1:
                self.logger.info(f"Found multiple requirements files, using: {requirements_file}")

        return requirements_files, requirements_file

    def _write_dockerfile(self, output_path: Path, content: str) -> None:
        """Write Dockerfile content to file.

        Args:
            output_path: Path to write to
            content: Dockerfile content

        Raises:
            FileOperationError: If writing fails
        """
        try:
            output_path.write_text(content, encoding="utf-8")
        except OSError as e:
            raise FileOperationError(
                f"Failed to write Dockerfile: {e}", file_path=str(output_path)
            ) from e

    def _write_k8s_manifest(self, force: bool, service_name: str, port: int) -> None:
        """Write k8s.yaml (Deployment + Service).

        No manifest was generated before, so users hand-rolled one -- usually with
        the default 30s termination grace period, which SIGKILLs an agent run
        mid-LLM-call on every rolling deploy. The generated one sets a grace period
        that matches how long a run can actually take, plus a preStop hook.

        Raises:
            FileOperationError: If writing fails
        """
        manifest_path = Path("k8s.yaml")

        if manifest_path.exists() and not force:
            raise FileOperationError(
                f"k8s.yaml already exists at {manifest_path}. Use --force to overwrite.",
                file_path=str(manifest_path),
            )

        content = generate_k8s_manifest_content(service_name, port)

        try:
            manifest_path.write_text(content, encoding="utf-8")
            self.output.success(f"Generated k8s.yaml at {manifest_path}")
        except OSError as e:
            raise FileOperationError(
                f"Failed to write k8s.yaml: {e}", file_path=str(manifest_path)
            ) from e

    def _write_docker_compose(self, force: bool, service_name: str, port: int) -> None:
        """Write docker-compose.yml file.

        Args:
            force: Overwrite existing file
            service_name: Service name to use
            port: Port to expose

        Raises:
            FileOperationError: If writing fails
        """
        compose_path = Path("docker-compose.yml")

        if compose_path.exists() and not force:
            raise FileOperationError(
                f"docker-compose.yml already exists at {compose_path}. Use --force to overwrite.",
                file_path=str(compose_path),
            )

        compose_content = generate_docker_compose_content(service_name, port)

        try:
            compose_path.write_text(compose_content, encoding="utf-8")
            self.output.success(f"Generated docker-compose.yml at {compose_path}")
        except OSError as e:
            raise FileOperationError(
                f"Failed to write docker-compose.yml: {e}", file_path=str(compose_path)
            ) from e

    def _show_next_steps(self, docker_compose: bool) -> None:
        """Show next steps to the user.

        Args:
            docker_compose: Whether docker-compose was generated
        """
        if docker_compose:
            steps = [
                "Review the generated Dockerfile and docker-compose.yml",
                "Build and run with: docker compose up --build",
                "Or build separately: docker build -t agentflow-cli .",
                "Access your API at: http://localhost:8000",
            ]
        else:
            steps = [
                "Review the generated Dockerfile",
                "Build the image: docker build -t agentflow-cli .",
                "Run the container: docker run -p 8000:8000 agentflow-cli",
                "Access your API at: http://localhost:8000",
            ]

        self.output.print_list(
            [f"{index}. {step}" for index, step in enumerate(steps, 1)],
            title="Next steps",
            bullet="→",
        )

        production_tips = [
            "Using a multi-stage build to reduce image size",
            "Setting up proper environment variables",
            "Configuring health checks and resource limits",
            "Using a reverse proxy like nginx",
        ]

        self.output.print_list(
            production_tips,
            title="Production considerations",
            bullet="•",
        )
